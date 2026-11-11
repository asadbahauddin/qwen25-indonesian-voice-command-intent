"""Sesi rekam gabungan (mic dipasang sekali) untuk DATA PENGEMBANGAN, bukan data uji.

Urutan:
  1. suasana : 30 s suasana lab tanpa bicara (uji pemicu palsu VAD)
  2. pilot   : membaca 36 kalimat pilot (bench/pilot_set.json) -> juga mengisi recordings/pilot_audio/<ID>/
  3. dev     : 18 kartu dev kalimat bebas (bench/kartu_dev.json)

Audio direkam TERUS-MENERUS (tanpa Enter mulai/berhenti per kalimat). Enter hanya menandai pindah ke item
berikutnya. Karena aliran lengkap disimpan, parameter VAD bisa diuji ulang offline berapa kali pun
(`python bench/tes_vad.py --dev <folder>`). VAD juga berjalan langsung sebagai umpan balik.

Kontrol: Enter = item selesai, lanjut | u = ulangi item ini | q = berhenti (semua tersimpan)

Keluaran: recordings/dev/<ID>_<ts>/{stream.wav, sesi.json}, klip dev di clips/,
          klip pilot di recordings/pilot_audio/<ID>/ + metadata.csv (status label final, karena dibaca).

Pemakaian:
    python bench/sesi_dev.py --penutur P01
    python bench/sesi_dev.py --penutur P01 --fase pilot dev      # lewati suasana
"""
import argparse
import json
import queue
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench.rekam_dataset import META_COLS, read_csv, write_csv  # noqa: E402
from src.audio_io import AudioSource, dbfs, save_wav  # noqa: E402
from src.utils import load_config, setup_logging  # noqa: E402
from src.vad import FRAME, SileroVAD, VADSegmenter  # noqa: E402

SUASANA_S = 30


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--penutur", required=True)
    ap.add_argument("--fase", nargs="+", default=["suasana", "pilot", "dev"], choices=["suasana", "pilot", "dev"])
    a = ap.parse_args()
    cfg = load_config()
    setup_logging(cfg, "sesi_dev")
    pid, host = a.penutur.strip().upper(), socket.gethostname()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sdir = cfg["paths"]["recordings"] / "dev" / f"{pid}_{ts}"
    (sdir / "clips").mkdir(parents=True, exist_ok=True)
    pilot = json.load(open(ROOT / cfg["dataset"]["pilot"], encoding="utf-8"))["items"]
    dev = json.load(open(ROOT / "bench" / "kartu_dev.json", encoding="utf-8"))["items"]
    proot = ROOT / cfg["dataset"]["out_baca"]
    (proot / pid).mkdir(parents=True, exist_ok=True)
    pmeta_p = proot / "metadata.csv"
    done_pilot = {r["item_id"] for r in read_csv(pmeta_p) if r["penutur"] == pid}
    done_dev = set()
    for p in (cfg["paths"]["recordings"] / "dev").glob(f"{pid}_*/sesi.json"):
        done_dev |= {m["item_id"] for m in json.load(open(p, encoding="utf-8"))["penanda"]
                     if m["fase"] == "dev" and m["valid"]}
    plan = []
    if "suasana" in a.fase:
        plan.append(("suasana", {"id": "AMB"}))
    if "pilot" in a.fase:
        plan += [("pilot", it) for it in pilot if it["id"] not in done_pilot]
    if "dev" in a.fase:
        plan += [("dev", it) for it in dev if it["id"] not in done_dev]
    print(f"{pid}: {len(plan)} item (pilot sudah {len(done_pilot)}/36, dev sudah {len(done_dev)}/18)")

    vcfg = cfg["vad"]
    seg = VADSegmenter(vcfg, SileroVAD(vcfg))
    lines = queue.Queue()
    def reader():
        while True:
            try:
                lines.put(input())
            except EOFError:
                lines.put("q")
                return
    threading.Thread(target=reader, daemon=True).start()
    chunks, natives, pend = [], [], np.zeros(0, np.float32)
    n16 = 0
    marks, vad_live = [], []
    clip_thr = cfg["levels"]["clip_threshold"]

    def pump(src):
        nonlocal pend, n16
        raw, x = src.read(timeout=2.0)
        chunks.append(x)
        natives.append((n16, float(np.max(np.abs(raw))) if len(raw) else 0.0, int(np.sum(np.abs(raw) >= clip_thr))))
        n16 += len(x)
        pend = np.concatenate([pend, x])
        while len(pend) >= FRAME:
            f, pend = pend[:FRAME], pend[FRAME:]
            ev = seg.process(f)
            if ev:
                vad_live.append({k: v for k, v in ev.items() if k != "audio"})
                print(f"      [VAD] ujaran {ev['durasi_s']:.1f} s", flush=True)

    sr = cfg["audio"]["target_samplerate"]
    try:
        with AudioSource(cfg["audio"]) as src:
            print(f"Mikrofon: {src.device_name} ({src.hostapi}) {src.in_sr} Hz -> 16 kHz. Merekam terus-menerus.\n")
            k = 0
            take = {}
            while k < len(plan):
                fase, it = plan[k]
                take[it["id"]] = take.get(it["id"], 0) + 1
                print("=" * 70)
                if fase == "suasana":
                    print(f"[SUASANA] Diam saja {SUASANA_S} detik (aktivitas lab biasa boleh).")
                    t0 = n16
                    while (n16 - t0) / sr < SUASANA_S:
                        pump(src)
                    marks.append({"fase": fase, "item_id": "AMB", "t0": t0 / sr, "t1": n16 / sr, "take": 1, "valid": True})
                    k += 1
                    continue
                n_amb = sum(f == "suasana" for f, _ in plan)
                print(f"[{k + 1 - n_amb}/{len(plan) - n_amb}] {fase.upper()} {it['id']} ({it['formality']})")
                if fase == "pilot":
                    print(f"  BACA   : {it['text']}")
                else:
                    print(f"  TUJUAN : {it['tujuan']}\n  GAYA   : {it['gaya']}\n  -> kalimat Anda SENDIRI")
                print("  Bicara kapan saja, lalu Enter = lanjut | u = ulangi | q = berhenti")
                t0 = n16
                while True:
                    pump(src)
                    try:
                        cmd = lines.get_nowait().strip().lower()
                        break
                    except queue.Empty:
                        pass
                m = {"fase": fase, "item_id": it["id"], "t0": t0 / sr, "t1": n16 / sr, "take": take[it["id"]],
                     "valid": cmd not in ("u", "q")}
                marks.append(m)
                if cmd == "q":
                    break
                if cmd == "u":
                    print("  diulang.")
                    continue
                w = [(c, p) for s, p, c in natives if t0 <= s < n16]
                clip = sum(c for c, _ in w)
                pk = dbfs(max((p for _, p in w), default=0.0))
                x = np.concatenate(chunks)[t0:n16]
                if clip:
                    print(f"  (catatan: clipping {clip} sampel)")
                if pk < cfg["dataset"]["min_peak_dbfs"]:
                    print("  PERINGATAN: sangat pelan / mic mati? ketik u lalu Enter pada item berikut bila perlu")
                if fase == "pilot":
                    wav = proot / pid / f"{pid}_{it['id']}.wav"
                    save_wav(wav, x, sr, cfg["audio"]["wav_subtype"])
                    rows = [r for r in read_csv(pmeta_p) if not (r["penutur"] == pid and r["item_id"] == it["id"])]
                    rows.append({"penutur": pid, "mode": "baca-sesi", "urutan": k, "item_id": it["id"],
                                 "formality": it["formality"], "intent_target": it["label"]["intent"],
                                 "target_json": json.dumps(it["label"], ensure_ascii=False), "teks_baca": it["text"],
                                 "tujuan": "", "wav": f"{pid}/{wav.name}", "durasi_s": round(len(x) / sr, 3),
                                 "peak_dbfs": round(pk, 2), "rms_dbfs": round(dbfs(np.sqrt(np.mean(x ** 2))), 2),
                                 "clip_native": clip, "take": take[it["id"]],
                                 "waktu": datetime.now().isoformat(timespec="seconds"), "host": host,
                                 "perangkat": src.device_name, "hostapi": src.hostapi, "sr_native": src.in_sr,
                                 "transkrip": it["text"], "label_final_json": json.dumps(it["label"], ensure_ascii=False),
                                 "status_label": "final (kalimat dibaca)",
                                 "catatan": f"sesi={sdir.name};t0={t0 / sr:.3f};t1={n16 / sr:.3f}"})
                    write_csv(pmeta_p, rows, META_COLS)
                else:
                    save_wav(sdir / "clips" / f"{pid}_{it['id']}.wav", x, sr, cfg["audio"]["wav_subtype"])
                k += 1
    except KeyboardInterrupt:
        print("\nDihentikan.")
    finally:
        if chunks:
            save_wav(sdir / "stream.wav", np.concatenate(chunks), sr, cfg["audio"]["wav_subtype"])
        json.dump({"penutur": pid, "host": host, "waktu": ts, "sr": sr, "config_vad": vcfg, "penanda": marks,
                   "vad_live": vad_live}, open(sdir / "sesi.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"\nTersimpan: {sdir.relative_to(ROOT)} ({n16 / sr / 60:.1f} menit, {sum(m['valid'] for m in marks)} item valid)")


if __name__ == "__main__":
    main()
