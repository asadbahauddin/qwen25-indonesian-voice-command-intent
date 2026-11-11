"""F3 - Benchmark Whisper base: openai-whisper vs faster-whisper, dengan/tanpa initial_prompt domain.

Masukan : WAV dataset responden (dataset/metadata.csv), 16 kHz mono.
Keluaran:
  dataset/asr_hipotesis_<host>_<ts>.csv   transkrip per file per konfigurasi (TIDAK di-push: data responden)
  results/asr_<host>_<ts>.{md,json}        ringkasan agregat: latency (rata-rata ± SD, n), RTF, WER bila referensi ada
WER dihitung hanya bila kolom `transkrip` di metadata.csv sudah terisi dan status_label = final/terkoreksi.
Normalisasi WER: huruf kecil, tanda baca dihapus (tanda hubung -> spasi), spasi ganda dirapikan.

Pemakaian:
    python bench/tes_asr.py                       # semua konfigurasi standar
    python bench/tes_asr.py --konfig faster:cuda:prompt openai:cuda:prompt
    python bench/tes_asr.py --hanya-wer dataset/asr_hipotesis_MSI_xxx.csv   # hitung ulang WER tanpa transkripsi
"""
import argparse
import csv
import io
import json
import re
import socket
import statistics as st
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import jiwer
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils import load_config, setup_logging  # noqa: E402

KONFIG_STD = ["faster:cuda:prompt", "faster:cuda:noprompt", "openai:cuda:prompt", "openai:cuda:noprompt",
              "faster:cpu:prompt", "openai:cpu:prompt"]
FINAL = {"final", "terkoreksi", "final (kalimat dibaca)"}


def norm(s):
    s = s.lower().replace("-", " ")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def wer_of(refs, hyps):
    refs, hyps = [norm(r) for r in refs], [norm(h) for h in hyps]
    o = jiwer.process_words(refs, hyps)
    n_ref = sum(len(r.split()) for r in refs)
    return {"wer": o.wer, "sub": o.substitutions, "del": o.deletions, "ins": o.insertions, "n_ref_kata": n_ref,
            "n_kalimat": len(refs)}


def msd(v):
    return (st.mean(v), st.stdev(v) if len(v) > 1 else 0.0, len(v))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--konfig", nargs="+", default=KONFIG_STD, help="backend:device:prompt|noprompt")
    ap.add_argument("--hanya-wer", help="CSV hipotesis yang sudah ada; lewati transkripsi")
    args = ap.parse_args()
    cfg = load_config()
    setup_logging(cfg, "tes_asr")
    dcfg = cfg["dataset"]
    droot = ROOT / dcfg["out_skenario"]
    meta = list(csv.DictReader(open(droot / "metadata.csv", encoding="utf-8")))
    host, ts = socket.gethostname(), datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.hanya_wer:
        hyp_rows = list(csv.DictReader(open(args.hanya_wer, encoding="utf-8")))
        loads = {}
    else:
        from src.asr import ASR
        hyp_rows, loads = [], {}
        audio = {(m["penutur"], m["item_id"]): sf.read(droot / m["wav"], dtype="float32")[0] for m in meta}
        for k in args.konfig:
            be, dev, pr = k.split(":")
            asr = ASR(cfg["asr"], ROOT, backend=be, device=dev, use_prompt=(pr == "prompt"))
            loads[k] = asr.load_s
            asr.transcribe(audio[next(iter(audio))])          # pemanasan (tidak dihitung)
            t0 = time.perf_counter()
            for i, m in enumerate(meta, 1):
                text, info = asr.transcribe(audio[(m["penutur"], m["item_id"])])
                hyp_rows.append({"konfig": k, "penutur": m["penutur"], "item_id": m["item_id"],
                                 "formality": m["formality"], "hipotesis": text, "t_asr": round(info["t_asr"], 4),
                                 "audio_s": round(info["audio_s"], 3), "compute": info["compute"],
                                 "prompt_sha": info["initial_prompt"] or ""})
                if i % 27 == 0:
                    print(f"  {k}: {i}/{len(meta)}", flush=True)
            print(f"{k}: selesai {time.perf_counter() - t0:.1f} s (load {asr.load_s:.2f} s)", flush=True)
            del asr
            if dev == "cuda":
                import torch
                torch.cuda.empty_cache()
        hp = droot / f"asr_hipotesis_{host}_{ts}.csv"
        with open(hp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(hyp_rows[0]))
            w.writeheader()
            w.writerows(hyp_rows)
        print("hipotesis ->", hp.relative_to(ROOT))

    ref = {(m["penutur"], m["item_id"]): m["transkrip"] for m in meta
           if m.get("transkrip", "").strip() and m.get("status_label", "") in FINAL}
    by = defaultdict(list)
    for r in hyp_rows:
        by[r["konfig"]].append(r)
    out = {"host": host, "waktu": ts, "n_file": len(meta), "n_referensi": len(ref), "konfig": {}}
    L = [f"# F3 Benchmark Whisper base ({host}, {ts})", "",
         f"Data: rekaman responden, n = {len(meta)} file. Referensi transkrip final: {len(ref)} file. "
         "Latency = waktu `transcribe()` per file setelah 1 pemanasan; RTF = t_asr / durasi audio.", "",
         "| Konfigurasi | Perangkat | Load (s) | t_asr (s) rata-rata ± SD | RTF rata-rata | n | WER |",
         "|---|---|---|---|---|---|---|"]
    for k, rows in by.items():
        t = [float(r["t_asr"]) for r in rows]
        rtf = [float(r["t_asr"]) / float(r["audio_s"]) for r in rows]
        m_, s_, n_ = msd(t)
        res = {"t_asr_mean": m_, "t_asr_sd": s_, "n": n_, "rtf_mean": st.mean(rtf), "load_s": loads.get(k),
               "compute": rows[0]["compute"]}
        wtxt = "–"
        pairs = [(ref[(r["penutur"], r["item_id"])], r["hipotesis"]) for r in rows if (r["penutur"], r["item_id"]) in ref]
        if pairs:
            res["wer"] = wer_of(*zip(*pairs))
            grp = defaultdict(list)
            for r in rows:
                key = (r["penutur"], r["item_id"])
                if key in ref:
                    grp["penutur=" + r["penutur"]].append((ref[key], r["hipotesis"]))
                    grp["formalitas=" + r["formality"]].append((ref[key], r["hipotesis"]))
            res["wer_per"] = {g: wer_of(*zip(*v)) for g, v in sorted(grp.items())}
            wtxt = f"{res['wer']['wer'] * 100:.2f}% (n={res['wer']['n_kalimat']})"
        out["konfig"][k] = res
        ld = f"{res['load_s']:.2f}" if res["load_s"] is not None else "–"
        L.append(f"| {k} | {res['compute']} | {ld} | {m_:.3f} ± {s_:.3f} | {res['rtf_mean']:.3f} | {n_} | {wtxt} |")
    if any("wer_per" in v for v in out["konfig"].values()):
        L += ["", "## WER per responden dan formalitas", ""]
        for k, v in out["konfig"].items():
            if "wer_per" in v:
                L.append(f"- **{k}**: " + "; ".join(f"{g} {x['wer'] * 100:.2f}% (n={x['n_kalimat']})"
                                                     for g, x in v["wer_per"].items()))
    md = ROOT / "results" / f"asr_{host}_{ts}.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    (ROOT / "results" / f"asr_{host}_{ts}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n".join(L))
    print("->", md.relative_to(ROOT))


if __name__ == "__main__":
    main()
