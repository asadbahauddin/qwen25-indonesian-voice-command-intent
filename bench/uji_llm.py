"""F6 - Uji pendahuluan teks: 3 metode NLU pada set pilot (masukan = teks ground-truth).

Metrik per metode (keseluruhan dan per formalitas):
  - Intent Accuracy
  - Exact Match (EM): intent + room/object/person/document + steps (urutan & isi) semuanya tepat
  - F1 weighted & macro (intent), confusion matrix (intent)
  - % JSON valid, % lolos skema
  - Latency NLU (t_nlu) rata-rata ± SD (n disebutkan); Qwen: load/prompt_eval/eval & token/s
Keluaran:
  results/uji_pilot_<host>_<waktu>.csv   (satu baris per kalimat x metode)
  results/uji_pilot_<host>_<waktu>.json  (semua metrik)
  results/summary_<host>_<waktu>.md      (tabel siap laporan)

Pemakaian:
    python bench/uji_llm.py                       # ketiga metode
    python bench/uji_llm.py --metode qwen rule    # sebagian
"""
import argparse
import csv
import json
import logging
import platform
import socket
import statistics as st
import sys
import time
from datetime import datetime
from pathlib import Path

from sklearn.metrics import confusion_matrix, f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.nlu.base import ENTITY_FIELDS, INTENTS, Domain, normalize_command  # noqa: E402
from src.utils import load_config, setup_logging  # noqa: E402

log = logging.getLogger("uji_llm")
FORMS = ["formal", "semi-formal", "informal"]
LABEL = {"qwen": "Qwen2.5 1.5B (Ollama)", "rule": "Rule-based", "indobert": "IndoBERT (fine-tuned)"}


def make_method(name, cfg, domain):
    if name == "qwen":
        from src.nlu.qwen import QwenNLU
        return QwenNLU(cfg, domain)
    if name == "rule":
        from src.nlu.rule import RuleNLU
        return RuleNLU(cfg, domain)
    if name == "indobert":
        from src.nlu.indobert import IndoBertNLU
        return IndoBertNLU(cfg, domain)
    raise ValueError(name)


def exact_match(pred, gold):
    if not isinstance(pred, dict):
        return False
    keys = ["intent", *ENTITY_FIELDS]
    if any(pred.get(k) != gold.get(k) for k in keys):
        return False
    ps, gs = pred.get("steps"), gold.get("steps")
    if gs is None or ps is None:
        return ps is None and gs is None
    if len(ps) != len(gs):
        return False
    return all(isinstance(p, dict) and all(p.get(k) == g.get(k) for k in keys) for p, g in zip(ps, gs))


def mean_sd(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None, 0
    return st.mean(xs), (st.stdev(xs) if len(xs) > 1 else 0.0), len(xs)


def fmt_ms(m, s, n, unit=1.0, d=3):
    return "-" if m is None else f"{m * unit:.{d}f} ± {s * unit:.{d}f}"


def metrics(rows):
    y_t = [r["gold_intent"] for r in rows]
    y_p = [r["pred_intent"] or "INVALID" for r in rows]
    n = len(rows)
    lab = [x for x in INTENTS if x in set(y_t) | set(y_p)]
    return {
        "n": n,
        "intent_acc": sum(a == b for a, b in zip(y_t, y_p)) / n,
        "exact_match": sum(r["exact_match"] for r in rows) / n,
        "f1_weighted": f1_score(y_t, y_p, labels=lab, average="weighted", zero_division=0),
        "f1_macro": f1_score(y_t, y_p, labels=lab, average="macro", zero_division=0),
        "json_valid": sum(r["json_valid"] for r in rows) / n,
        "schema_valid": sum(r["schema_valid"] for r in rows) / n,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metode", nargs="+", default=["qwen", "rule", "indobert"], choices=["qwen", "rule", "indobert"])
    ap.add_argument("--data", default="bench/pilot_set.json")
    ap.add_argument("--qwen-prompt", choices=["v1", "v2"], default=None,
                    help="override nlu.qwen.prompt_version (untuk perbandingan)")
    ap.add_argument("--qwen-schema", choices=["v1", "v2"], default=None,
                    help="override nlu.qwen.schema_version (untuk perbandingan)")
    args = ap.parse_args()

    cfg = load_config()
    setup_logging(cfg, "uji_llm")
    if args.qwen_prompt:
        cfg["nlu"]["qwen"]["prompt_version"] = args.qwen_prompt
    if args.qwen_schema:
        cfg["nlu"]["qwen"]["schema_version"] = args.qwen_schema
    domain = Domain(ROOT / cfg["nlu"]["domain_vocab"])
    data = json.load(open(ROOT / args.data, encoding="utf-8"))
    items = data["items"]
    host, stamp = socket.gethostname(), datetime.now().strftime("%Y%m%d_%H%M%S")
    res_dir = cfg["paths"]["results"]

    all_rows, summary = [], {"host": host, "waktu": stamp, "platform": platform.platform(),
                             "data": args.data, "data_versi": data["_meta"].get("versi"), "n_kalimat": len(items),
                             "masukan": "teks ground-truth", "skema_validasi": "v2", "metode": {}}
    for mname in args.metode:
        m = make_method(mname, cfg, domain)
        warm = m.warmup()
        log.info("%s warm-up: %s", mname, warm)
        meta = {"warmup": warm}
        if mname == "qwen":
            meta.update(model=m.q["model"], prompt_version=m.prompt_version, prompt_sha=m.prompt_sha,
                        use_schema=m.q["use_schema"], schema_version=m.schema_version, plan_field=m.plan_field)
        elif mname == "rule":
            meta.update(keywords_version=m.version)
        else:
            meta.update(device=str(m.device))
        rows = []
        t_run = time.perf_counter()
        for it in items:
            gold = normalize_command(it["label"], domain)
            pred, info = m.predict(it["text"])
            r = {"metode": mname, "id": it["id"], "formality": it["formality"], "text": it["text"],
                 "gold_intent": gold["intent"], "pred_intent": pred.get("intent") if isinstance(pred, dict) else None,
                 "intent_ok": isinstance(pred, dict) and pred.get("intent") == gold["intent"],
                 "exact_match": exact_match(pred, gold), "json_valid": bool(info.get("json_valid")),
                 "schema_valid": bool(info.get("schema_valid")), "t_nlu": info.get("t_nlu"),
                 "load_s": info.get("load_s"), "prompt_eval_s": info.get("prompt_eval_s"),
                 "prompt_tokens": info.get("prompt_tokens"), "eval_s": info.get("eval_s"),
                 "eval_tokens": info.get("eval_tokens"), "tokens_per_s": info.get("tokens_per_s"),
                 "error": info.get("error"), "tindakan": json.dumps(info.get("tindakan"), ensure_ascii=False),
                 "pred_json": json.dumps(pred, ensure_ascii=False), "gold_json": json.dumps(gold, ensure_ascii=False)}
            rows.append(r)
            log.info("%s %s intent=%s EM=%s t=%.3f", mname, it["id"], r["intent_ok"], r["exact_match"], r["t_nlu"])
        meta["durasi_run_s"] = time.perf_counter() - t_run
        res = {"keseluruhan": metrics(rows), "per_formalitas": {f: metrics([r for r in rows if r["formality"] == f])
                                                               for f in FORMS}}
        lat = {}
        for k in ["t_nlu", "load_s", "prompt_eval_s", "eval_s", "tokens_per_s", "prompt_tokens", "eval_tokens"]:
            mu, sd, n = mean_sd([r[k] for r in rows])
            if n:
                lat[k] = {"mean": mu, "sd": sd, "n": n}
        res["latency"] = lat
        y_t = [r["gold_intent"] for r in rows]
        y_p = [r["pred_intent"] or "INVALID" for r in rows]
        labs = INTENTS + (["INVALID"] if "INVALID" in y_p else [])
        res["confusion_matrix"] = {"labels": labs, "matrix": confusion_matrix(y_t, y_p, labels=labs).tolist()}
        res["salah"] = [{"id": r["id"], "formality": r["formality"], "text": r["text"], "gold": json.loads(r["gold_json"]),
                         "pred": json.loads(r["pred_json"]), "intent_ok": r["intent_ok"], "error": r["error"]}
                        for r in rows if not r["exact_match"]]
        res["meta"] = meta
        summary["metode"][mname] = res
        all_rows += rows
        o = res["keseluruhan"]
        print(f"{mname:9s} n={o['n']} intent_acc={o['intent_acc']:.4f} EM={o['exact_match']:.4f} "
              f"F1w={o['f1_weighted']:.4f} F1m={o['f1_macro']:.4f} json={o['json_valid']:.2f} "
              f"t_nlu={fmt_ms(lat['t_nlu']['mean'], lat['t_nlu']['sd'], lat['t_nlu']['n'])} s", flush=True)

    # ---- simpan
    csv_p = res_dir / f"uji_pilot_{host}_{stamp}.csv"
    with open(csv_p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        w.writeheader()
        w.writerows(all_rows)
    json_p = res_dir / f"uji_pilot_{host}_{stamp}.json"
    json_p.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    # ---- ringkasan markdown (kolom sesuai CLAUDE.md bagian 8)
    L = [f"# Ringkasan uji pendahuluan (F6) — {host} — {stamp}", "",
         f"Data: `{args.data}` (versi {summary['data_versi']}), {len(items)} kalimat, masukan = teks ground-truth. "
         f"Platform: {summary['platform']}.", "",
         "## Tabel akurasi", "",
         "| Metode | Jumlah kalimat uji | Intent Accuracy | Exact Match | F1 weighted | F1 macro | JSON valid |",
         "|---|---|---|---|---|---|---|"]
    for mname, res in summary["metode"].items():
        o = res["keseluruhan"]
        L.append(f"| {LABEL[mname]} | {o['n']} | {o['intent_acc'] * 100:.2f}% | {o['exact_match'] * 100:.2f}% | "
                 f"{o['f1_weighted']:.4f} | {o['f1_macro']:.4f} | {o['json_valid'] * 100:.1f}% |")
    L += ["", "## Per formalitas (Intent Accuracy / Exact Match)", "",
          "| Metode | " + " | ".join(f"{f} (n)" for f in FORMS) + " |", "|---|" + "---|" * len(FORMS)]
    for mname, res in summary["metode"].items():
        cells = [f"{res['per_formalitas'][f]['intent_acc'] * 100:.1f}% / {res['per_formalitas'][f]['exact_match'] * 100:.1f}%"
                 f" ({res['per_formalitas'][f]['n']})" for f in FORMS]
        L.append(f"| {LABEL[mname]} | " + " | ".join(cells) + " |")
    L += ["", "## Tabel latency (tahap NLU saja, masukan teks)", "",
          "| Platform | VAD (s) | Whisper (s) | Qwen2.5 (s) | Total (s) |", "|---|---|---|---|---|"]
    if "qwen" in summary["metode"]:
        q = summary["metode"]["qwen"]["latency"]["t_nlu"]
        L.append(f"| {host} (laptop, RTX 2050) | – | – | {fmt_ms(q['mean'], q['sd'], q['n'])} (n={q['n']}) | "
                 f"{fmt_ms(q['mean'], q['sd'], q['n'])} (n={q['n']}) |")
    L += ["", "VAD dan Whisper tidak dipakai pada uji teks (diukur di F5/F9).", "",
          "Latency NLU semua metode (rata-rata ± SD, detik):", "",
          "| Metode | t_nlu (s) | n |", "|---|---|---|"]
    for mname, res in summary["metode"].items():
        t = res["latency"]["t_nlu"]
        L.append(f"| {LABEL[mname]} | {fmt_ms(t['mean'], t['sd'], t['n'], d=4)} | {t['n']} |")
    if "qwen" in summary["metode"]:
        ql = summary["metode"]["qwen"]["latency"]
        L += ["", "Rincian Qwen2.5 (dari Ollama, rata-rata ± SD):", "",
              "| load (s) | prompt_eval (s) | prompt token | eval (s) | eval token | token/s |", "|---|---|---|---|---|---|",
              "| " + " | ".join(fmt_ms(ql[k]["mean"], ql[k]["sd"], ql[k]["n"], d=(1 if "tokens" in k else 3))
                              for k in ["load_s", "prompt_eval_s", "prompt_tokens", "eval_s", "eval_tokens",
                                        "tokens_per_s"]) + " |"]
    for mname, res in summary["metode"].items():
        cm = res["confusion_matrix"]
        L += ["", f"## Confusion matrix intent — {LABEL[mname]} (baris = label, kolom = prediksi)", "",
              "| label \\ prediksi | " + " | ".join(cm["labels"]) + " |", "|---|" + "---|" * len(cm["labels"])]
        for lab, row in zip(cm["labels"], cm["matrix"]):
            L.append(f"| {lab} | " + " | ".join(str(v) for v in row) + " |")
    L += ["", "## Kalimat yang tidak Exact Match", ""]
    for mname, res in summary["metode"].items():
        L.append(f"**{LABEL[mname]}** ({len(res['salah'])} kalimat)")
        L.append("")
        for s in res["salah"]:
            L.append(f"- {s['id']} ({s['formality']}) \"{s['text']}\" — intent {'benar' if s['intent_ok'] else 'SALAH'}"
                     f"{'; ' + s['error'] if s['error'] else ''}  ")
            L.append(f"  label: `{json.dumps(s['gold'], ensure_ascii=False)}`  ")
            L.append(f"  prediksi: `{json.dumps(s['pred'], ensure_ascii=False)}`")
        L.append("")
    L += [f"File detail: `{csv_p.name}`, `{json_p.name}`."]
    md_p = res_dir / f"summary_{host}_{stamp}.md"
    md_p.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nRingkasan: {md_p}\nCSV: {csv_p}\nJSON: {json_p}")


if __name__ == "__main__":
    main()
