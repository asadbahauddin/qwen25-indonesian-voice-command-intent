"""F9 - Evaluasi penuh pipeline: 3 metode NLU x 3 masukan x platform (laptop GPU / laptop CPU).

Masukan NLU per item:
  teks : transkrip ground-truth (memisahkan galat NLU dari galat ASR)
  utuh : rekaman utuh -> Whisper -> NLU
  vad  : rekaman -> Silero VAD (simulasi streaming, segmen disambung) -> Whisper -> NLU  (= pipeline lengkap)
Metrik: WER (utuh, vad); Intent Accuracy, Exact Match, F1 weighted/macro, confusion matrix, % JSON valid,
        per formalitas dan per penutur; latency per tahap rata-rata ± SD (n), t_total dan t_respons.
Definisi metrik sama dengan F3 (bench/tes_asr.py: wer_of) dan F6 (bench/uji_llm.py: exact_match, metrics).

Data:
  --data pilot   : recordings/pilot_audio (set PENGEMBANGAN, untuk uji coba alat ini)
  --data dataset : dataset/ (set UJI; hanya item ber-transkrip terkoreksi DAN berlabel final)

Keluaran:
  results/eval_<data>_<host>_<ts>.{md,json}        agregat (aman di-push)
  <folder data>/eval_item_<data>_<host>_<ts>.csv   per item (lokal; dataset tidak di-push)

Pemakaian:
    python bench/evaluasi.py --data pilot
    python bench/evaluasi.py --data dataset --perangkat gpu cpu
"""
import argparse
import csv
import io
import json
import logging
import platform
import socket
import statistics as st
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import soundfile as sf
from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench.tes_asr import FINAL, wer_of  # noqa: E402
from bench.uji_llm import exact_match, metrics  # noqa: E402
from src.nlu.base import INTENTS, normalize_command  # noqa: E402
from src.pipeline import METHODS, Pipeline  # noqa: E402
from src.utils import load_config, ram_tersedia_gb, setup_logging  # noqa: E402

log = logging.getLogger("evaluasi")
FORMS = ["formal", "semi-formal", "informal"]
MASUKAN = ["teks", "utuh", "vad"]
NAMA = {"qwen": "Qwen2.5 1.5B", "rule": "Rule-based", "indobert": "IndoBERT"}
PLATFORM = {"gpu": "Laptop GPU (RTX 2050)", "cpu": "Laptop CPU (i5-12450H)"}


def load_items(cfg, data):
    root = ROOT / cfg["dataset"]["out_baca" if data == "pilot" else "out_skenario"]
    rows = list(csv.DictReader(open(root / "metadata.csv", encoding="utf-8")))
    items, skip = [], 0
    for r in rows:
        if not (r.get("transkrip", "").strip() and r.get("label_final_json", "").strip()
                and r.get("status_label", "") in FINAL):
            skip += 1
            continue
        items.append({"penutur": r["penutur"], "item_id": r["item_id"], "formality": r["formality"],
                      "ref": r["transkrip"].strip(), "gold": json.loads(r["label_final_json"]), "wav": root / r["wav"]})
    return root, items, skip


def msd(v):
    v = [x for x in v if x is not None]
    if not v:
        return None
    return {"mean": st.mean(v), "sd": st.stdev(v) if len(v) > 1 else 0.0, "n": len(v)}


def f(m, d=3):
    return "–" if not m else f"{m['mean']:.{d}f} ± {m['sd']:.{d}f}"


def run(pipe, items, methods, masukan, n_warm):
    """Return daftar baris per (masukan, metode, item) untuk perangkat aktif pipeline."""
    rows = []
    for k, it in enumerate([*items[:n_warm], *items]):
        warm = k < n_warm
        x = sf.read(str(it["wav"]), dtype="float32")[0]
        recs = {}
        if "teks" in masukan:
            recs["teks"] = pipe.from_text(it["ref"], methods)
        if "utuh" in masukan:
            recs["utuh"] = pipe.from_audio(x, methods, sumber="utuh", file=str(it["wav"].name))
        if "vad" in masukan:
            recs["vad"] = pipe.from_file(it["wav"], methods, pakai_vad=True)
        if warm:
            continue
        for mk, rec in recs.items():
            for mname in methods:
                h = rec["hasil"].get(mname)
                pred, info = (h["json"], h["info"]) if h else (None, {"error": "tanpa segmen VAD"})
                if str(info.get("error") or "").startswith("ollama:"):
                    # server mati/tak terjangkau = galat infrastruktur, BUKAN kesalahan model -> hentikan
                    sys.exit(f"BERHENTI: Ollama tidak bisa dihubungi ({it['item_id']}, {mk}). Jalankan `ollama serve`, "
                             f"lalu ulangi. Detail: {info['error'][:200]}")
                gold = it["gold"]
                rows.append({
                    "perangkat": pipe.device, "masukan": mk, "metode": mname, "penutur": it["penutur"],
                    "item_id": it["item_id"], "formality": it["formality"], "ref": it["ref"],
                    "hipotesis": rec["transkrip"] if mk != "teks" else "", "n_segmen_vad": rec.get("n_segmen_vad"),
                    "gold_intent": gold["intent"],
                    "pred_intent": pred.get("intent") if isinstance(pred, dict) else None,
                    "exact_match": exact_match(pred, gold),
                    "json_valid": bool(info.get("json_valid")), "schema_valid": bool(info.get("schema_valid", info.get("json_valid"))),
                    "pred_json": json.dumps(pred, ensure_ascii=False), "error": info.get("error"),
                    "t_vad": rec["t_vad"], "t_tunggu_vad": rec["t_tunggu_vad"], "t_asr": rec["t_asr"],
                    "t_nlu": info.get("t_nlu"), "t_total": h["t_total"] if h else None,
                    "t_respons": h["t_respons"] if h else None, "audio_s": rec["audio_s"],
                    "qwen_tokens_per_s": info.get("tokens_per_s"), "ram_tersedia_gb": rec.get("ram_tersedia_gb")})
        i = k - n_warm + 1
        if i % 9 == 0 or i == len(items):
            print(f"  [{pipe.device}] {i}/{len(items)}  RAM tersedia {ram_tersedia_gb() or 0:.1f} GB", flush=True)
    return rows


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", choices=["pilot", "dataset"], required=True)
    ap.add_argument("--perangkat", nargs="+", choices=["gpu", "cpu"], default=["gpu", "cpu"])
    ap.add_argument("--masukan", nargs="+", choices=MASUKAN, default=MASUKAN)
    ap.add_argument("--metode", nargs="+", choices=METHODS, default=METHODS)
    ap.add_argument("--pemanasan", type=int, default=3, help="item awal dijalankan dulu dan TIDAK dihitung, per perangkat")
    ap.add_argument("--batas", type=int, help="hanya N item pertama (uji alat)")
    ap.add_argument("--sensitivitas", help="JSON dari bench/cek_kebocoran.py: akurasi juga dihitung TANPA item 'mirip'")
    a = ap.parse_args()
    try:
        from transformers.utils import logging as hf_logging
        hf_logging.disable_progress_bar()
    except Exception:
        pass
    cfg = load_config()
    setup_logging(cfg, "evaluasi")
    for h in logging.getLogger().handlers:
        if type(h) is logging.StreamHandler:
            h.setLevel(logging.WARNING)
    cfg["pipeline"]["csv_log"] = None            # per item dicatat di CSV evaluasi sendiri
    root, items, skip = load_items(cfg, a.data)
    if a.batas:
        items = items[: a.batas]
    if not items:
        sys.exit(f"Tidak ada item siap uji di {root} (lewati {skip}: transkrip/label belum final).")
    host, ts = socket.gethostname(), datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"{a.data}: {len(items)} item (dilewati {skip} belum final), perangkat {a.perangkat}, masukan {a.masukan}, "
          f"metode {a.metode}, pemanasan {a.pemanasan}. RAM tersedia awal {ram_tersedia_gb() or 0:.1f} GB")
    ollama = None
    if "qwen" in a.metode:
        import requests
        host_o = cfg["nlu"]["qwen"]["host"].rstrip("/")
        try:
            ver = requests.get(host_o + "/api/version", timeout=5).json()["version"]
            tags = {m["name"]: m["digest"] for m in requests.get(host_o + "/api/tags", timeout=5).json()["models"]}
        except Exception as e:
            sys.exit(f"Ollama tidak bisa dihubungi di {host_o} ({e}). Jalankan `ollama serve` (bukan aplikasi, "
                     "agar pembaruan otomatis tidak terpasang), lalu ulangi.")
        ollama = {"versi": ver, "model": cfg["nlu"]["qwen"]["model"], "digest": tags.get(cfg["nlu"]["qwen"]["model"])}
        print(f"Ollama {ver}, {ollama['model']} digest {str(ollama['digest'])[:12]}")
    pipe = Pipeline(cfg)
    for it in items:
        it["gold"] = normalize_command(it["gold"], pipe.domain)
    rows, durasi = [], {}
    for dev in a.perangkat:
        t0 = time.perf_counter()
        pipe.set_device(dev)
        pipe.load_asr()
        for m in a.metode:
            pipe.method(m)
        rows += run(pipe, items, a.metode, a.masukan, min(a.pemanasan, len(items)))
        durasi[dev] = time.perf_counter() - t0

    # ---------------- per item (lokal) ----------------
    ip = root / f"eval_item_{a.data}_{host}_{ts}.csv"
    with open(ip, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # ---------------- agregat ----------------
    asr = cfg["asr"]
    out = {"host": host, "waktu": ts, "platform": platform.platform(), "data": a.data, "n_item": len(items),
           "dilewati_belum_final": skip, "pemanasan_dibuang": a.pemanasan, "durasi_s": durasi,
           "asr": {k: asr[k] for k in ("backend", "model", "beam_size", "use_initial_prompt")},
           "vad": {k: cfg["vad"][k] for k in ("threshold", "min_silence_ms", "pre_roll_ms")},
           "qwen": {k: cfg["nlu"]["qwen"][k] for k in ("model", "prompt_version", "schema_version")}, "ollama": ollama,
           "ram_tersedia_gb_min": min((r["ram_tersedia_gb"] for r in rows if r["ram_tersedia_gb"]), default=None),
           "wer": {}, "akurasi": {}, "latency": {}, "confusion": {}}
    G = defaultdict(list)
    for r in rows:
        G[(r["perangkat"], r["masukan"], r["metode"])].append(r)
    # WER: satu transkrip per (perangkat, masukan) -> ambil baris metode pertama
    for dev in a.perangkat:
        for mk in [m for m in a.masukan if m != "teks"]:
            rr = G[(dev, mk, a.metode[0])]
            res = {"semua": wer_of([r["ref"] for r in rr], [r["hipotesis"] for r in rr])}
            for key in ("formality", "penutur"):
                for v in sorted({r[key] for r in rr}):
                    sub = [r for r in rr if r[key] == v]
                    res[f"{key}={v}"] = wer_of([r["ref"] for r in sub], [r["hipotesis"] for r in sub])
            out["wer"][f"{dev}/{mk}"] = res
    for (dev, mk, mname), rr in G.items():
        key = f"{dev}/{mk}/{mname}"
        acc = {"semua": metrics(rr)}
        for k2 in ("formality", "penutur"):
            for v in sorted({r[k2] for r in rr}):
                acc[f"{k2}={v}"] = metrics([r for r in rr if r[k2] == v])
        out["akurasi"][key] = acc
        lab = INTENTS + ["INVALID"]
        cm = confusion_matrix([r["gold_intent"] for r in rr], [r["pred_intent"] or "INVALID" for r in rr], labels=lab)
        out["confusion"][key] = {"label": lab, "matriks": cm.tolist()}
        out["latency"][key] = {c: msd([r[c] for r in rr]) for c in ("t_vad", "t_asr", "t_nlu", "t_total", "t_respons")}
        out["latency"][key]["qwen_tokens_per_s"] = msd([r["qwen_tokens_per_s"] for r in rr])
    mirip = set()
    if a.sensitivitas:
        kb = json.load(open(a.sensitivitas, encoding="utf-8"))
        mirip = {x["item"] for v in kb["sumber"].values() for x in v["mirip"]}
        out["sensitivitas"] = {"sumber": str(a.sensitivitas), "dikeluarkan": sorted(mirip), "akurasi": {}}
        for (dev, mk, mname), rr in G.items():
            sub = [r for r in rr if f"{r['penutur']}_{r['item_id']}" not in mirip]
            out["sensitivitas"]["akurasi"][f"{dev}/{mk}/{mname}"] = {
                "semua": metrics(sub), **{f"formality={x}": metrics([r for r in sub if r["formality"] == x])
                                          for x in FORMS if any(r["formality"] == x for r in sub)}}

    # ---------------- laporan ----------------
    n = len(items)
    L = [f"# F9 Evaluasi pipeline — data {a.data} ({host}, {ts})", "",
         f"- Data: **{a.data}** ({'set pengembangan, uji coba alat' if a.data == 'pilot' else 'set uji'}), n = {n} item"
         f"{f', dilewati {skip} (belum final)' if skip else ''}; {a.pemanasan} item pertama dijalankan dulu sebagai pemanasan (tidak dihitung).",
         f"- Whisper {asr['model']} ({asr['backend']}, beam {asr['beam_size']}, initial_prompt {asr['use_initial_prompt']}); "
         f"VAD threshold {cfg['vad']['threshold']}, min_silence {cfg['vad']['min_silence_ms']} ms; "
         f"Qwen {cfg['nlu']['qwen']['model']} prompt {cfg['nlu']['qwen']['prompt_version']} skema {cfg['nlu']['qwen']['schema_version']}"
         + (f" (Ollama {ollama['versi']}, digest {str(ollama['digest'])[:12]})." if ollama else "."),
         f"- Masukan: teks = transkrip ground-truth; utuh = rekaman utuh → Whisper; vad = VAD → Whisper (pipeline lengkap).",
         f"- RAM tersedia minimum selama uji: {out['ram_tersedia_gb_min'] or 0:.2f} GB.", ""]
    L += ["## Tabel latency (pipeline lengkap: VAD → Whisper → Qwen2.5)", "",
          f"Rata-rata ± SD dalam detik, n = {n} ujaran per platform. Total = VAD + Whisper + Qwen2.5 (komputasi). "
          f"Waktu respons = jeda tunggu VAD ({cfg['vad']['min_silence_ms']} ms) + Whisper + Qwen2.5.", "",
          "| Platform | VAD (s) | Whisper (s) | Qwen2.5 (s) | Total (s) | Waktu respons (s) |", "|---|---|---|---|---|---|"]
    for dev in a.perangkat:
        lt = out["latency"].get(f"{dev}/vad/qwen")
        if lt:
            L.append(f"| {PLATFORM[dev]} | {f(lt['t_vad'], 4)} | {f(lt['t_asr'])} | {f(lt['t_nlu'])} | {f(lt['t_total'])} | {f(lt['t_respons'])} |")
    L += ["", "Latency NLU per metode (masukan vad):", "", "| Platform | Metode | NLU (s) | Total (s) | Waktu respons (s) |",
          "|---|---|---|---|---|"]
    for dev in a.perangkat:
        for mname in a.metode:
            lt = out["latency"].get(f"{dev}/vad/{mname}")
            if lt:
                L.append(f"| {PLATFORM[dev]} | {NAMA[mname]} | {f(lt['t_nlu'])} | {f(lt['t_total'])} | {f(lt['t_respons'])} |")
    L += ["", "## WER Whisper", "", "| Platform | Masukan | WER | sub/del/ins | formal | semi-formal | informal |",
          "|---|---|---|---|---|---|---|"]
    for k, v in out["wer"].items():
        dev, mk = k.split("/")
        s = v["semua"]
        per = [f"{v[f'formality={x}']['wer'] * 100:.2f}%" if f"formality={x}" in v else "–" for x in FORMS]
        L.append(f"| {PLATFORM[dev]} | {mk} | {s['wer'] * 100:.2f}% (n={s['n_kalimat']}) | {s['sub']}/{s['del']}/{s['ins']} | " + " | ".join(per) + " |")
    for dev in a.perangkat:
        L += ["", f"## Tabel akurasi — {PLATFORM[dev]}", "",
              "| Metode | Masukan | Jumlah kalimat uji | Intent Accuracy | Exact Match | F1 weighted | F1 macro | JSON valid |",
              "|---|---|---|---|---|---|---|---|"]
        for mk in a.masukan:
            for mname in a.metode:
                m = out["akurasi"].get(f"{dev}/{mk}/{mname}", {}).get("semua")
                if m:
                    L.append(f"| {NAMA[mname]} | {mk} | {m['n']} | {m['intent_acc'] * 100:.2f}% | {m['exact_match'] * 100:.2f}% | "
                             f"{m['f1_weighted']:.4f} | {m['f1_macro']:.4f} | {m['json_valid'] * 100:.1f}% |")
        L += ["", "Per formalitas (Intent Accuracy / Exact Match):", "",
              "| Metode | Masukan | formal | semi-formal | informal |", "|---|---|---|---|---|"]
        for mk in a.masukan:
            for mname in a.metode:
                acc = out["akurasi"].get(f"{dev}/{mk}/{mname}", {})
                cells = []
                for x in FORMS:
                    m = acc.get(f"formality={x}")
                    cells.append(f"{m['intent_acc'] * 100:.1f} / {m['exact_match'] * 100:.1f} (n={m['n']})" if m else "–")
                L.append(f"| {NAMA[mname]} | {mk} | " + " | ".join(cells) + " |")
        if len({it["penutur"] for it in items}) > 1:
            L += ["", "Per penutur (Intent Accuracy / Exact Match, masukan vad):", ""]
            pen = sorted({it["penutur"] for it in items})
            L += ["| Metode | " + " | ".join(pen) + " |", "|---" * (len(pen) + 1) + "|"]
            for mname in a.metode:
                acc = out["akurasi"].get(f"{dev}/vad/{mname}", {})
                L.append(f"| {NAMA[mname]} | " + " | ".join(
                    f"{acc[f'penutur={p}']['intent_acc'] * 100:.1f} / {acc[f'penutur={p}']['exact_match'] * 100:.1f}"
                    if f"penutur={p}" in acc else "–" for p in pen) + " |")
    if mirip:
        L += ["", f"## Uji sensitivitas: tanpa {len(mirip)} item 'mirip' data latih/prompt ({', '.join(sorted(mirip))})", "",
              "Intent Accuracy / Exact Match (%): semua item → tanpa item mirip.", "",
              "| Platform | Metode | Masukan | Semua | Tanpa item mirip |", "|---|---|---|---|---|"]
        for dev in a.perangkat:
            for mk in a.masukan:
                for mname in a.metode:
                    k2 = f"{dev}/{mk}/{mname}"
                    s1, s2 = out["akurasi"][k2]["semua"], out["sensitivitas"]["akurasi"][k2]["semua"]
                    L.append(f"| {PLATFORM[dev]} | {NAMA[mname]} | {mk} | {s1['intent_acc'] * 100:.2f} / {s1['exact_match'] * 100:.2f} "
                             f"(n={s1['n']}) | {s2['intent_acc'] * 100:.2f} / {s2['exact_match'] * 100:.2f} (n={s2['n']}) |")
    # hipotesis (dihitung, bukan klaim): H1 formal+semi Qwen > 80%, H2 informal Qwen vs baseline, H3 total < 15 s
    L += ["", "## Ringkasan hipotesis (angka dihitung otomatis; interpretasi oleh peneliti)", ""]
    for dev in a.perangkat:
        for mk in [m for m in ("vad", "teks") if m in a.masukan]:
            rr = [r for r in G[(dev, mk, "qwen")] if r["formality"] in ("formal", "semi-formal")]
            if rr:
                acc = sum(r["gold_intent"] == r["pred_intent"] for r in rr) / len(rr)
                L.append(f"- H1 [{PLATFORM[dev]}, {mk}]: intent accuracy Qwen formal+semi-formal = {acc * 100:.2f}% "
                         f"(n={len(rr)}) → {'> 80%' if acc > 0.8 else '≤ 80%'}")
            inf = {m: out["akurasi"].get(f"{dev}/{mk}/{m}", {}).get("formality=informal") for m in a.metode}
            if all(inf.values()):
                L.append(f"- H2 [{PLATFORM[dev]}, {mk}]: intent accuracy informal: " +
                         ", ".join(f"{NAMA[m]} {v['intent_acc'] * 100:.1f}%" for m, v in inf.items()) +
                         "; EM: " + ", ".join(f"{NAMA[m]} {v['exact_match'] * 100:.1f}%" for m, v in inf.items()))
        lt = out["latency"].get(f"{dev}/vad/qwen")
        if lt and lt["t_respons"]:
            mx = max(r["t_respons"] for r in G[(dev, "vad", "qwen")] if r["t_respons"] is not None)
            L.append(f"- H3 [{PLATFORM[dev]}]: waktu respons Qwen {lt['t_respons']['mean']:.3f} ± {lt['t_respons']['sd']:.3f} s, "
                     f"maks {mx:.3f} s → {'< 15 s' if mx < 15 else '≥ 15 s (ada ujaran melewati 15 s)'}")
    L += ["", f"Confusion matrix lengkap per (platform, masukan, metode) ada di file JSON. Per item: `{ip.relative_to(ROOT)}` (lokal)."]
    md = cfg["paths"]["results"] / f"eval_{a.data}_{host}_{ts}.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    md.with_suffix(".json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(L))
    print("->", md.relative_to(ROOT))


if __name__ == "__main__":
    main()
