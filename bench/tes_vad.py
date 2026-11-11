"""F2 - Uji Silero VAD + pre-roll.

Mode dataset (default), memakai 162 rekaman responden:
  1. Probabilitas Silero per frame (32 ms) dihitung sekali per file (torch dan onnx; waktu per frame dicatat,
     selisih probabilitas torch vs onnx dicek).
  2. Rentang ucapan acuan dari energi frame (> --ambang-db dBFS). Andal karena noise gate transmitter
     membuat bagian diam ±-91 dBFS.
  3. Sapuan parameter threshold x min_silence_ms (state machine disimulasikan pada probabilitas yang sama):
     jumlah segmen per file (target tepat 1), awal/akhir ucapan terpotong, jeda akhir.
  4. Konfigurasi aktif (config.yaml: vad): audio hasil segmentasi ditranskrip faster-whisper dan dibandingkan
     dengan transkrip audio utuh (hasil F3).
Mode mic (--mic): segmentasi real-time dari mikrofon, ujaran disimpan ke recordings/vad/seg_*.wav.

Keluaran: results/vad_<host>_<ts>.{md,json}

Pemakaian:
    python bench/tes_vad.py
    python bench/tes_vad.py --tanpa-asr
    python bench/tes_vad.py --mic [--detik 60]
"""
import argparse
import copy
import csv
import io
import json
import re
import socket
import statistics as st
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils import load_config, setup_logging  # noqa: E402
from src.vad import FRAME, SR, SileroVAD, VADSegmenter, frames_of  # noqa: E402

TH = [0.3, 0.5, 0.7]
SIL = [300, 500, 800, 1000, 1200, 1500]


class CachedVAD:
    """Mengganti model dengan probabilitas yang sudah dihitung (untuk sapuan parameter)."""

    def __init__(self, probs):
        self.p, self.i = probs, 0

    def reset(self):
        pass

    def prob(self, _):
        self.i += 1
        return self.p[self.i - 1]


def simulate(x16, probs, vcfg):
    seg = VADSegmenter(vcfg, CachedVAD(probs))
    out = []
    for f in frames_of(x16):
        ev = seg.process(f)
        if ev:
            out.append(ev)
    ev = seg.flush()
    if ev:
        out.append(ev)
    return out


def energy_span(x16, thr_db, min_run=4):
    """Rentang ucapan acuan: frame > thr_db; deretan aktif < min_run frame (128 ms) diabaikan
    (bunyi klik tombol Enter push-to-talk di awal/akhir rekaman). Return (awal_s, akhir_s, jeda_internal_maks_s)."""
    f = x16[: len(x16) // FRAME * FRAME].reshape(-1, FRAME)
    e = 20 * np.log10(np.sqrt((f ** 2).mean(1)) + 1e-10)
    m = np.concatenate([[0], (e > thr_db).astype(int), [0]])
    d = np.diff(m)
    runs = [(s, t) for s, t in zip(np.where(d == 1)[0], np.where(d == -1)[0]) if t - s >= min_run]
    if not runs:
        return None
    gaps = [b[0] - a[1] for a, b in zip(runs, runs[1:])]
    return runs[0][0] * FRAME / SR, runs[-1][1] * FRAME / SR, (max(gaps) if gaps else 0) * FRAME / SR


def norm(s):
    s = s.lower().replace("-", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def msd(v):
    return f"{st.mean(v):.3f} ± {st.stdev(v):.3f}" if len(v) > 1 else f"{v[0]:.3f}"


def run_dataset(cfg, args):
    vbase = cfg["vad"]
    droot = ROOT / cfg["dataset"]["out_skenario"]
    meta = list(csv.DictReader(open(droot / "metadata.csv", encoding="utf-8")))
    audio = {(m["penutur"], m["item_id"]): sf.read(droot / m["wav"], dtype="float32")[0] for m in meta}
    res, L = {"n_file": len(meta), "config_vad": vbase}, []

    # 1. probabilitas + waktu per frame
    probs, timing = {}, {}
    for onnx in (False, True):
        vad = SileroVAD({**vbase, "onnx": onnx})
        dts, P = [], {}
        for k, x in audio.items():
            vad.reset()
            pk = []
            for f in frames_of(x):
                t0 = time.perf_counter()
                pk.append(vad.prob(f))
                dts.append(time.perf_counter() - t0)
            P[k] = pk
        name = "onnx" if onnx else "torch"
        probs[name] = P
        timing[name] = {"load_s": vad.load_s, "ms_per_frame_mean": st.mean(dts) * 1000,
                        "ms_per_frame_sd": st.stdev(dts) * 1000, "n_frame": len(dts),
                        "rtf": st.mean(dts) / (FRAME / SR)}
        print(f"{name}: {timing[name]['ms_per_frame_mean']:.3f} ms/frame (n={len(dts)})", flush=True)
    diff = max(abs(a - b) for k in audio for a, b in zip(probs["torch"][k], probs["onnx"][k]))
    res["timing"], res["selisih_prob_torch_onnx_maks"] = timing, diff
    use = "onnx" if vbase["onnx"] else "torch"
    P = probs[use]

    # 2. acuan energi
    ref = {k: energy_span(x, args.ambang_db) for k, x in audio.items()}
    gaps = [r[2] for r in ref.values() if r]
    res["jeda_internal_maks_s"] = {"mean": st.mean(gaps), "p90": float(np.percentile(gaps, 90)), "max": max(gaps)}

    # 3. sapuan
    L += ["## Sapuan parameter (pre_roll {} ms, post_pad {} ms, min_speech {} ms)".format(
        vbase["pre_roll_ms"], vbase["post_pad_ms"], vbase["min_speech_ms"]), "",
        "| threshold | min_silence (ms) | tepat 1 segmen | 0 segmen | >1 segmen (terpecah) | awal terpotong | "
        "akhir terpotong |", "|---|---|---|---|---|---|---|"]
    res["sapuan"] = []
    for th in TH:
        for sil in SIL:
            vc = {**vbase, "threshold": th, "min_silence_ms": sil}
            nseg, cut0, cut1, split = Counter(), 0, 0, []
            for k, x in audio.items():
                segs = simulate(x, P[k], vc)
                nseg[min(len(segs), 2)] += 1
                if len(segs) > 1:
                    split.append(f"{k[0]}_{k[1]}")
                r = ref[k]
                if segs and r:
                    cut0 += segs[0]["start_s"] > r[0] + 1e-9
                    cut1 += segs[-1]["end_s"] < r[1] - 1e-9
            row = {"threshold": th, "min_silence_ms": sil, "n1": nseg[1], "n0": nseg[0], "n_lebih": nseg[2],
                   "awal_terpotong": cut0, "akhir_terpotong": cut1, "terpecah": split}
            res["sapuan"].append(row)
            mark = " ←aktif" if th == vbase["threshold"] and sil == vbase["min_silence_ms"] else ""
            L.append(f"| {th} | {sil}{mark} | {nseg[1]}/{len(audio)} | {nseg[0]} | {nseg[2]} | {cut0} | {cut1} |")

    # 4. konfigurasi aktif: detail + ASR
    det = []
    for k, x in audio.items():
        segs = simulate(x, P[k], vbase)
        r = ref[k]
        det.append({"k": k, "segs": segs, "ref": r,
                    "lead": (r[0] - segs[0]["start_s"]) if segs and r else None,
                    "tail": (segs[-1]["end_s"] - r[1]) if segs and r else None})
    lead = [d["lead"] for d in det if d["lead"] is not None]
    tail = [d["tail"] for d in det if d["tail"] is not None]
    dur_full = [len(audio[d["k"]]) / SR for d in det]
    dur_seg = [sum(s["durasi_s"] for s in d["segs"]) for d in det]
    res["aktif"] = {"margin_awal_s": lead and {"mean": st.mean(lead), "min": min(lead)},
                    "margin_akhir_s": tail and {"mean": st.mean(tail), "min": min(tail)},
                    "durasi_utuh_mean": st.mean(dur_full), "durasi_segmen_mean": st.mean(dur_seg)}
    if not args.tanpa_asr:
        from src.asr import ASR
        hp = max(droot.glob("asr_hipotesis_*.csv"), key=lambda p: p.stat().st_mtime)
        full = {(r["penutur"], r["item_id"]): r["hipotesis"] for r in csv.DictReader(open(hp, encoding="utf-8"))
                if r["konfig"] == "faster:cuda:prompt"}
        asr = ASR(cfg["asr"], ROOT, backend="faster", device="cuda", use_prompt=True)
        asr.transcribe(audio[det[0]["k"]])
        same, refs, hyps, ta_full, ta_seg = 0, [], [], [], []
        for d in det:
            seg_audio = np.concatenate([s["audio"] for s in d["segs"]]) if d["segs"] else np.zeros(FRAME, np.float32)
            t, info = asr.transcribe(seg_audio)
            ta_seg.append(info["t_asr"])
            same += norm(t) == norm(full[d["k"]])
            refs.append(norm(full[d["k"]]) or "-")
            hyps.append(norm(t))
        import jiwer
        res["asr"] = {"hipotesis_utuh": hp.name, "identik": same, "n": len(det),
                      "wer_segmen_vs_utuh": jiwer.wer(refs, hyps), "t_asr_segmen": st.mean(ta_seg)}

    # tulis
    t = timing
    head = ["| Implementasi | Load (s) | Waktu per frame 32 ms (ms) | RTF | n frame |", "|---|---|---|---|---|"]
    for n in ("torch", "onnx"):
        head.append(f"| {n}{' ←aktif' if n == use else ''} | {t[n]['load_s']:.2f} | {t[n]['ms_per_frame_mean']:.3f} ± "
                    f"{t[n]['ms_per_frame_sd']:.3f} | {t[n]['rtf']:.3f} | {t[n]['n_frame']} |")
    a = res["aktif"]
    act = ["", f"## Konfigurasi aktif: threshold {vbase['threshold']}, min_silence {vbase['min_silence_ms']} ms", "",
           f"- Margin awal (awal segmen sebelum awal energi ucapan): rata-rata {a['margin_awal_s']['mean']:.3f} s, "
           f"minimum {a['margin_awal_s']['min']:.3f} s",
           f"- Margin akhir: rata-rata {a['margin_akhir_s']['mean']:.3f} s, minimum {a['margin_akhir_s']['min']:.3f} s",
           f"- Durasi audio: utuh {a['durasi_utuh_mean']:.2f} s → segmen VAD {a['durasi_segmen_mean']:.2f} s (rata-rata)",
           f"- Jeda internal terpanjang per ujaran (acuan energi): rata-rata {res['jeda_internal_maks_s']['mean']:.3f} s, "
           f"p90 {res['jeda_internal_maks_s']['p90']:.3f} s, maks {res['jeda_internal_maks_s']['max']:.3f} s"]
    if "asr" in res:
        r = res["asr"]
        act.append(f"- Whisper (faster, GPU, prompt) pada segmen VAD vs audio utuh: identik {r['identik']}/{r['n']}, "
                   f"WER segmen-vs-utuh {r['wer_segmen_vs_utuh'] * 100:.2f}%, t_asr segmen rata-rata {r['t_asr_segmen']:.3f} s")
    return res, ["## Waktu komputasi Silero VAD (CPU laptop, 1 thread)", "",
                 f"Selisih probabilitas torch vs onnx maksimum: {diff:.2e}", ""] + head + [""] + L + act


ATURAN_PILIH = ("min_silence terkecil (lalu threshold paling dekat 0,5) dengan: ujaran terpecah <= 5% item, "
                "0 item terlewat, 0 awal/akhir terpotong, 0 pemicu palsu saat suasana")


def run_dev(cfg, args):
    """Analisis offline sesi pengembangan (bench/sesi_dev.py). Aturan pilih ditetapkan sebelum data ada."""
    vbase = {**cfg["vad"], "onnx": True}
    L, res = [f"Aturan pemilihan (ditetapkan 12 Nov 2026 sebelum data dev direkam): {ATURAN_PILIH}.", ""], {"sesi": []}
    data = []
    for d in args.dev:
        d = Path(d)
        ses = json.load(open(d / "sesi.json", encoding="utf-8"))
        x = sf.read(d / "stream.wav", dtype="float32")[0]
        vad = SileroVAD(vbase)
        vad.reset()
        P = [vad.prob(f) for f in frames_of(x)]
        live = simulate(x, P, ses["config_vad"])
        res["sesi"].append({"folder": d.name, "menit": len(x) / SR / 60, "n_penanda_valid": sum(m["valid"] for m in ses["penanda"]),
                            "vad_live": len(ses["vad_live"]), "vad_offline_config_sama": len(live)})
        data.append((ses, x, P))
    L += ["| Sesi | Durasi (menit) | Item valid | Ujaran VAD live | Simulasi offline (config sama) |", "|---|---|---|---|---|"]
    L += [f"| {r['folder']} | {r['menit']:.1f} | {r['n_penanda_valid']} | {r['vad_live']} | {r['vad_offline_config_sama']} |"
          for r in res["sesi"]]
    L += ["", "| threshold | min_silence (ms) | tepat 1 (pilot) | tepat 1 (dev) | terpecah | terlewat | pemicu palsu (suasana) | "
          "awal terpotong | akhir terpotong | lolos |", "|---|---|---|---|---|---|---|---|---|---|"]
    rows = []
    for th in TH:
        for sil in SIL:
            vc = {**vbase, "threshold": th, "min_silence_ms": sil}
            c = Counter()
            for ses, x, P in data:
                segs = simulate(x, P, vc)
                for m in ses["penanda"]:
                    if not m["valid"]:
                        continue
                    inw = [g for g in segs if m["t0"] <= (g["start_s"] + g["end_s"]) / 2 < m["t1"]]
                    if m["fase"] == "suasana":
                        c["palsu"] += len(inw)
                        continue
                    c["n_" + m["fase"]] += 1
                    c["satu_" + m["fase"]] += len(inw) == 1
                    c["pecah"] += len(inw) > 1
                    c["lewat"] += len(inw) == 0
                    i0, i1 = int(m["t0"] * SR), int(m["t1"] * SR)
                    r = energy_span(x[i0:i1], args.ambang_db)
                    if r and inw:
                        c["cut0"] += inw[0]["start_s"] > m["t0"] + r[0] + 1e-9
                        c["cut1"] += inw[-1]["end_s"] < m["t0"] + r[1] - 1e-9
            n = c["n_pilot"] + c["n_dev"]
            row = {"threshold": th, "min_silence_ms": sil, **c, "n": n}
            row["lolos"] = (n > 0 and c["pecah"] <= 0.05 * n and c["lewat"] == 0 and c["cut0"] == 0 and c["cut1"] == 0
                            and c["palsu"] == 0)
            rows.append(row)
            L.append(f"| {th} | {sil} | {c['satu_pilot']}/{c['n_pilot']} | {c['satu_dev']}/{c['n_dev']} | {c['pecah']} | "
                     f"{c['lewat']} | {c['palsu']} | {c['cut0']} | {c['cut1']} | {'ya' if row['lolos'] else '–'} |")
    ok = sorted([r for r in rows if r["lolos"]], key=lambda r: (r["min_silence_ms"], abs(r["threshold"] - 0.5)))
    res["sapuan"], res["terpilih"] = rows, ok[0] if ok else None
    L += ["", f"**Terpilih:** threshold {ok[0]['threshold']}, min_silence {ok[0]['min_silence_ms']} ms" if ok
          else "**Tidak ada kombinasi yang lolos aturan**: perlu dibahas dengan peneliti."]
    return res, L


def run_mic(cfg, args):
    from src.audio_io import AudioSource
    vcfg = cfg["vad"]
    vad = SileroVAD(vcfg)
    seg = VADSegmenter(vcfg, vad)
    out = cfg["paths"]["recordings"] / "vad"
    out.mkdir(parents=True, exist_ok=True)
    from src.audio_io import save_wav
    buf = np.zeros(0, np.float32)
    rows = []
    print(f"Bicara ke mikrofon ({args.detik} s). Ctrl+C untuk berhenti.")
    with AudioSource(cfg["audio"]) as src:
        t_end = time.perf_counter() + args.detik
        try:
            while time.perf_counter() < t_end:
                _, x = src.read(timeout=2.0)
                buf = np.concatenate([buf, x])
                while len(buf) >= FRAME:
                    f, buf = buf[:FRAME], buf[FRAME:]
                    ev = seg.process(f)
                    if ev:
                        t_emit = time.perf_counter()
                        p = out / f"seg_{datetime.now():%Y%m%d_%H%M%S}.wav"
                        save_wav(p, ev["audio"], SR, cfg["audio"]["wav_subtype"])
                        rows.append({k: v for k, v in ev.items() if k != "audio"} | {"wav": p.name})
                        print(f"  ujaran {ev['durasi_s']:.2f} s ({ev['alasan']}), komputasi VAD {ev['t_vad'] * 1000:.1f} ms,"
                              f" jeda akhir {ev['tunggu_akhir_s']:.2f} s -> {p.name}", flush=True)
                        _ = t_emit
        except KeyboardInterrupt:
            pass
    return {"mode": "mic", "ujaran": rows}, [f"## Uji mic real-time ({args.detik} s)", "",
                                             f"Ujaran terdeteksi: {len(rows)}"] + \
        [f"- {r['wav']}: {r['durasi_s']:.2f} s, {r['alasan']}, komputasi VAD {r['t_vad'] * 1000:.1f} ms" for r in rows]


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mic", action="store_true")
    ap.add_argument("--detik", type=float, default=60)
    ap.add_argument("--tanpa-asr", action="store_true")
    ap.add_argument("--dev", nargs="+", help="folder sesi dari bench/sesi_dev.py (recordings/dev/<ID>_<ts>)")
    ap.add_argument("--ambang-db", type=float, default=-45.0, help="ambang energi frame untuk acuan ucapan")
    args = ap.parse_args()
    cfg = load_config()
    setup_logging(cfg, "tes_vad")
    host, ts = socket.gethostname(), datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.dev:
        res, lines = run_dev(cfg, args)
    else:
        res, lines = run_mic(cfg, args) if args.mic else run_dataset(cfg, args)
    lines = [f"# F2 Uji Silero VAD ({host}, {ts})", ""] + lines
    tag = "dev_" if args.dev else ("mic_" if args.mic else "")
    md = ROOT / "results" / f"vad_{tag}{host}_{ts}.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (md.with_suffix(".json")).write_text(json.dumps(copy.deepcopy(res), indent=2, default=float), encoding="utf-8")
    print("\n".join(lines))
    print("->", md.relative_to(ROOT))


if __name__ == "__main__":
    main()
