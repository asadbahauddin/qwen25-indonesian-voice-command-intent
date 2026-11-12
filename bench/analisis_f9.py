"""F9 lanjutan - analisis dari CSV per item bench/evaluasi.py:
  1. Precision/recall/F1 per intent
  2. Uji McNemar eksak (binomial, dua sisi) antar metode pada item yang sama (intent benar & Exact Match)
  3. Jenis kesalahan: intent salah vs intent benar tetapi entity/steps salah (field mana)
  4. Dampak ASR: item benar pada teks tetapi salah pada transkrip (vad)
  5. Pencilan latency (waktu respons > 15 s) beserta RAM tersedia saat itu

    python bench/analisis_f9.py dataset/eval_item_dataset_<host>_<ts>.csv
Keluaran: results/analisis_<data>_<host>_<ts>.{md,json} (agregat + ID item, tanpa kalimat responden).
"""
import argparse
import csv
import io
import json
import socket
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from scipy.stats import binomtest
from sklearn.metrics import precision_recall_fscore_support

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.nlu.base import ENTITY_FIELDS, INTENTS, Domain, normalize_command  # noqa: E402
from src.utils import load_config  # noqa: E402

NAMA = {"qwen": "Qwen2.5 1.5B", "rule": "Rule-based", "indobert": "IndoBERT"}
B = lambda x: x in (True, "True", "true", "1")  # noqa: E731


def mcnemar(a, b):
    """a, b: daftar bool (benar/salah) per item yang sama. Return (b01, b10, p) uji binomial eksak dua sisi."""
    n01 = sum((not x) and y for x, y in zip(a, b))
    n10 = sum(x and (not y) for x, y in zip(a, b))
    p = binomtest(n10, n01 + n10, 0.5).pvalue if n01 + n10 else 1.0
    return n10, n01, p


def field_err(pred, gold):
    if not isinstance(pred, dict):
        return ["json_invalid"]
    if pred.get("intent") != gold["intent"]:
        return ["intent"]
    out = [f for f in ENTITY_FIELDS if pred.get(f) != gold.get(f)]
    ps, gs = pred.get("steps"), gold.get("steps")
    if (ps is None) != (gs is None):
        out.append("steps")
    elif gs is not None:
        if len(ps) != len(gs):
            out.append("steps_jumlah")
        else:
            for p, g in zip(ps, gs):
                if p.get("intent") != g.get("intent"):
                    out.append("steps_intent")
                    break
                if any(p.get(f) != g.get(f) for f in ENTITY_FIELDS):
                    out.append("steps_entity")
                    break
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    a = ap.parse_args()
    cfg = load_config()
    dom = Domain(ROOT / cfg["nlu"]["domain_vocab"])
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    data = "dataset" if "dataset" in Path(a.csv).name else "pilot"
    mroot = ROOT / cfg["dataset"]["out_skenario" if data == "dataset" else "out_baca"]
    gold = {(m["penutur"], m["item_id"]): normalize_command(json.loads(m["label_final_json"]), dom)
            for m in csv.DictReader(open(mroot / "metadata.csv", encoding="utf-8")) if m["label_final_json"].strip()}
    G = defaultdict(list)
    for r in rows:
        G[(r["perangkat"], r["masukan"], r["metode"])].append(r)
    devs = sorted({r["perangkat"] for r in rows}, key=lambda x: x != "gpu")
    mks = [m for m in ("teks", "utuh", "vad") if any(r["masukan"] == m for r in rows)]
    mets = [m for m in ("qwen", "rule", "indobert") if any(r["metode"] == m for r in rows)]
    host, ts = socket.gethostname(), datetime.now().strftime("%Y%m%d_%H%M%S")
    out = {"sumber": str(a.csv), "per_intent": {}, "mcnemar": {}, "kesalahan": {}, "asr": {}, "pencilan": {}}
    L = [f"# F9 analisis lanjutan — {data} ({host}, {ts})", "", f"Sumber per item: `{Path(a.csv).name}`.", ""]

    # 1. per intent
    L += ["## 1. F1 per intent (laptop GPU)", "",
          "Kelas seimbang (27 item per intent), sehingga F1 weighted = F1 macro.", ""]
    for mk in [m for m in ("teks", "vad") if m in mks]:
        L += [f"**Masukan {mk}** — F1 (precision / recall):", "", "| Intent | " + " | ".join(NAMA[m] for m in mets) + " |",
              "|---" * (len(mets) + 1) + "|"]
        res = {}
        for m in mets:
            rr = G[(devs[0], mk, m)]
            p, r_, f, s = precision_recall_fscore_support([x["gold_intent"] for x in rr],
                                                          [x["pred_intent"] or "INVALID" for x in rr],
                                                          labels=INTENTS, zero_division=0)
            res[m] = {i: {"p": p[k], "r": r_[k], "f1": f[k], "n": int(s[k])} for k, i in enumerate(INTENTS)}
        out["per_intent"][f"{devs[0]}/{mk}"] = res
        for i in INTENTS:
            L.append(f"| {i} | " + " | ".join(f"{res[m][i]['f1']:.2f} ({res[m][i]['p']:.2f} / {res[m][i]['r']:.2f})" for m in mets) + " |")
        L.append("")

    # 2. McNemar
    L += ["## 2. Uji McNemar eksak (dua sisi), item yang sama", "",
          "b = A benar & B salah, c = A salah & B benar; p < 0,05 = beda bermakna.", "",
          "| Platform | Masukan | Metrik | A vs B | b | c | p |", "|---|---|---|---|---|---|---|"]
    for dev in devs:
        for mk in mks:
            idx = {m: {(x["penutur"], x["item_id"]): x for x in G[(dev, mk, m)]} for m in mets}
            keys = sorted(idx[mets[0]])
            for met, fn in (("intent", lambda x: x["gold_intent"] == x["pred_intent"]), ("EM", lambda x: B(x["exact_match"]))):
                for A, Bm in (("qwen", "rule"), ("qwen", "indobert"), ("rule", "indobert")):
                    if A in idx and Bm in idx:
                        b, c, p = mcnemar([fn(idx[A][k]) for k in keys], [fn(idx[Bm][k]) for k in keys])
                        out["mcnemar"][f"{dev}/{mk}/{met}/{A}-{Bm}"] = {"b": b, "c": c, "p": p}
                        L.append(f"| {dev} | {mk} | {met} | {NAMA[A]} vs {NAMA[Bm]} | {b} | {c} | {p:.4f}{' *' if p < 0.05 else ''} |")
    # Qwen GPU vs CPU (determinisme lintas platform)
    if len(devs) > 1 and "qwen" in mets:
        L += ["", "Qwen laptop GPU vs laptop CPU (item yang sama):", ""]
        for mk in mks:
            g = {(x["penutur"], x["item_id"]): x for x in G[("gpu", mk, "qwen")]}
            c_ = {(x["penutur"], x["item_id"]): x for x in G[("cpu", mk, "qwen")]}
            ks = sorted(set(g) & set(c_))
            beda = sum(g[k]["pred_json"] != c_[k]["pred_json"] for k in ks)
            b, c, p = mcnemar([B(g[k]["exact_match"]) for k in ks], [B(c_[k]["exact_match"]) for k in ks])
            out["mcnemar"][f"gpu-cpu/{mk}/EM/qwen"] = {"b": b, "c": c, "p": p, "json_berbeda": beda}
            L.append(f"- {mk}: keluaran JSON berbeda pada {beda}/{len(ks)} item; EM GPU-benar/CPU-salah {b}, sebaliknya {c}, p = {p:.4f}")

    # 3. jenis kesalahan
    L += ["", "## 3. Jenis kesalahan (laptop GPU)", "",
          "Kolom = item salah EM; dipecah: intent salah, atau intent benar tetapi field tertentu salah (satu item bisa >1 field).", "",
          "| Metode | Masukan | Salah EM | intent | room | object | person | document | steps* | JSON tak valid |", "|---|---|---|---|---|---|---|---|---|---|"]
    for mk in mks:
        for m in mets:
            cnt, nerr = Counter(), 0
            for x in G[(devs[0], mk, m)]:
                if B(x["exact_match"]):
                    continue
                nerr += 1
                pred = json.loads(x["pred_json"]) if x["pred_json"] not in ("", "null") else None
                for e in field_err(pred, gold[(x["penutur"], x["item_id"])]):
                    cnt[e] += 1
            out["kesalahan"][f"{devs[0]}/{mk}/{m}"] = {"salah_em": nerr, **cnt}
            st = sum(v for k, v in cnt.items() if k.startswith("steps"))
            L.append(f"| {NAMA[m]} | {mk} | {nerr} | {cnt['intent']} | {cnt['room']} | {cnt['object']} | {cnt['person']} | "
                     f"{cnt['document']} | {st} | {cnt['json_invalid']} |")
    L += ["", "*steps = combined_command: jumlah langkah / intent langkah / entity langkah salah.", ""]
    # confusion utama Qwen teks
    for m in mets:
        pairs = Counter((x["gold_intent"], x["pred_intent"]) for x in G[(devs[0], "teks", m)]
                        if x["gold_intent"] != x["pred_intent"])
        out["kesalahan"][f"{devs[0]}/teks/{m}/pasangan"] = [[g, p, n] for (g, p), n in pairs.most_common()]
        L.append(f"- Pasangan intent tertukar terbanyak, {NAMA[m]} (teks): " +
                 (", ".join(f"{g}→{p} ({n})" for (g, p), n in pairs.most_common(4)) or "tidak ada"))

    # 4. dampak ASR
    if "teks" in mks and "vad" in mks:
        L += ["", "## 4. Dampak galat ASR (laptop GPU): EM benar pada teks → salah pada transkrip VAD", "",
              "| Metode | Benar di teks | ... tetap benar di vad | ... jadi salah | salah di teks tapi benar di vad |", "|---|---|---|---|---|"]
        for m in mets:
            t = {(x["penutur"], x["item_id"]): B(x["exact_match"]) for x in G[(devs[0], "teks", m)]}
            v = {(x["penutur"], x["item_id"]): B(x["exact_match"]) for x in G[(devs[0], "vad", m)]}
            ok = [k for k in t if t[k]]
            res = {"benar_teks": len(ok), "tetap": sum(v[k] for k in ok), "jadi_salah": sum(not v[k] for k in ok),
                   "salah_jadi_benar": sum((not t[k]) and v[k] for k in t)}
            out["asr"][m] = res
            L.append(f"| {NAMA[m]} | {res['benar_teks']} | {res['tetap']} | {res['jadi_salah']} | {res['salah_jadi_benar']} |")

    # 5. pencilan latency
    L += ["", "## 5. Pencilan waktu respons > 15 s (masukan vad)", ""]
    for dev in devs:
        for m in mets:
            rr = [x for x in G[(dev, "vad", m)] if x["t_respons"] and float(x["t_respons"]) > 15]
            out["pencilan"][f"{dev}/{m}"] = [{"item": f"{x['penutur']}_{x['item_id']}", "t_respons": float(x["t_respons"]),
                                             "t_asr": float(x["t_asr"] or 0), "t_nlu": float(x["t_nlu"] or 0),
                                             "ram_gb": float(x["ram_tersedia_gb"] or 0)} for x in rr]
            if rr:
                L.append(f"- {dev}/{NAMA[m]}: {len(rr)}/{len(G[(dev, 'vad', m)])} ujaran — " + "; ".join(
                    f"{x['penutur']}_{x['item_id']} {float(x['t_respons']):.1f} s (ASR {float(x['t_asr'] or 0):.1f}, NLU {float(x['t_nlu'] or 0):.1f}, RAM {float(x['ram_tersedia_gb'] or 0):.2f} GB)"
                    for x in sorted(rr, key=lambda x: -float(x["t_respons"]))[:6]))
        ram = [float(x["ram_tersedia_gb"]) for x in G[(dev, "vad", "qwen")] if x["ram_tersedia_gb"]]
        if ram:
            L.append(f"- RAM tersedia saat uji {dev}: min {min(ram):.2f} GB, median {sorted(ram)[len(ram) // 2]:.2f} GB")
    md = cfg["paths"]["results"] / f"analisis_{data}_{host}_{ts}.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    md.with_suffix(".json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("\n".join(L))
    print("->", md.relative_to(ROOT))


if __name__ == "__main__":
    main()
