"""F8 - Alat perekaman dataset (push-to-talk: Enter mulai, Enter berhenti).

Mode:
  skenario : responden membaca KARTU SKENARIO lalu mengucapkan perintah dengan kalimatnya sendiri
             (kalimat bebas) -> dataset/<penutur>/  + dataset/metadata.csv + dataset/responden.csv
  baca     : penutur membacakan kalimat pilot -> recordings/pilot_audio/<penutur>/ + metadata.csv

Fitur:
  - WAV 16 kHz mono PCM_16 (lewat src/audio_io.py: native -> mono -> soxr)
  - cek otomatis setelah tiap rekaman: durasi, puncak, clipping (sinyal native) -> peringatan
  - pilihan: [Enter] simpan & lanjut, u = ulang, p = putar, s = lewati, q = keluar
  - bisa dilanjutkan: item yang sudah tersimpan untuk penutur tsb dilewati
  - urutan kartu diacak per penutur (seed dari id penutur) untuk mengurangi efek urutan

Pemakaian:
    python bench/rekam_dataset.py --mode baca --penutur P01
    python bench/rekam_dataset.py --mode skenario --penutur R01
"""
import argparse
import csv
import json
import random
import socket
import sys
import threading
import time
import zlib
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.audio_io import AudioSource, dbfs, save_wav  # noqa: E402
from src.utils import load_config, setup_logging  # noqa: E402

META_COLS = ["penutur", "mode", "urutan", "item_id", "formality", "intent_target", "target_json", "teks_baca",
             "tujuan", "wav", "durasi_s", "peak_dbfs", "rms_dbfs", "clip_native", "take", "waktu", "host",
             "perangkat", "hostapi", "sr_native", "transkrip", "label_final_json", "status_label", "catatan"]
RESP_COLS = ["penutur", "usia", "jenis_kelamin", "bahasa_ibu", "persetujuan", "tanggal"]


def read_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p, rows, cols):
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)


def ask_respondent(path, pid):
    rows = read_csv(path)
    if any(r["penutur"] == pid for r in rows):
        return
    print(f"\nData responden baru {pid} (tanpa nama; nama hanya di lembar persetujuan kertas)")
    ok = input("  Lembar persetujuan sudah ditandatangani? (y/n): ").strip().lower()
    if ok != "y":
        sys.exit("Perekaman dibatalkan: persetujuan responden wajib.")
    rows.append({"penutur": pid, "usia": input("  Usia (tahun): ").strip(),
                 "jenis_kelamin": input("  Jenis kelamin (L/P/-): ").strip().upper(),
                 "bahasa_ibu": input("  Bahasa ibu (mis. Madura/Jawa/Indonesia): ").strip(),
                 "persetujuan": "ya", "tanggal": datetime.now().strftime("%Y-%m-%d")})
    write_csv(path, rows, RESP_COLS)


def record_ptt(src, max_s, tail_s):
    """Rekam sampai Enter ditekan (atau max_s). Return (raw_native, x16, berhenti_otomatis)."""
    stop = threading.Event()
    t = threading.Thread(target=lambda: (input(), stop.set()), daemon=True)
    src.drain()
    raw, res = [], []
    t0 = time.perf_counter()
    t.start()
    auto = False
    while not stop.is_set():
        r, o = src.read(timeout=2.0)
        raw.append(r)
        res.append(o)
        if time.perf_counter() - t0 >= max_s:
            auto = True
            break
    t_end = time.perf_counter() + tail_s
    while not auto and time.perf_counter() < t_end:
        r, o = src.read(timeout=2.0)
        raw.append(r)
        res.append(o)
    res.append(src.flush())
    if auto:
        print(f"\n    (berhenti otomatis setelah {max_s:.0f} s) tekan Enter...", end="", flush=True)
        t.join()
    return np.concatenate(raw), np.concatenate(res), auto


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["skenario", "baca"], required=True)
    ap.add_argument("--penutur", required=True, help="ID anonim, mis. R01 (responden) atau P01 (pilot)")
    ap.add_argument("--tanpa-acak", action="store_true", help="urutan item tidak diacak")
    args = ap.parse_args()

    cfg = load_config()
    setup_logging(cfg, "rekam_dataset")
    dcfg, acfg, lcfg = cfg["dataset"], cfg["audio"], cfg["levels"]
    pid = args.penutur.strip().upper()
    if args.mode == "skenario":
        items = json.load(open(ROOT / dcfg["skenario"], encoding="utf-8"))["items"]
        out_root = ROOT / dcfg["out_skenario"]
    else:
        items = json.load(open(ROOT / dcfg["pilot"], encoding="utf-8"))["items"]
        out_root = ROOT / dcfg["out_baca"]
    out_dir = out_root / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_p = out_root / "metadata.csv"
    if args.mode == "skenario":
        ask_respondent(out_root / "responden.csv", pid)

    order = list(range(len(items)))
    if args.mode == "skenario" and not args.tanpa_acak:
        random.Random(zlib.crc32(pid.encode())).shuffle(order)
    meta = read_csv(meta_p)
    done = {r["item_id"] for r in meta if r["penutur"] == pid}
    todo = [i for i in order if items[i]["id"] not in done]
    print(f"\n{pid}: {len(items) - len(todo)}/{len(items)} sudah terekam, sisa {len(todo)}.")
    if not todo:
        return

    host = socket.gethostname()
    with AudioSource(acfg) as src:
        print(f"Mikrofon: {src.device_name} ({src.hostapi}), {src.in_sr} Hz -> 16 kHz\n")
        for n, i in enumerate(todo, 1):
            it = items[i]
            take = 0
            while True:
                print("=" * 70)
                print(f"[{len(items) - len(todo) + n}/{len(items)}] {it['id']}  ({it['formality']})")
                if args.mode == "skenario":
                    print(f"  TUJUAN : {it['tujuan']}")
                    print(f"  GAYA   : {it['gaya']}")
                    print("  -> Ucapkan perintah ke robot dengan kalimat Anda SENDIRI.")
                else:
                    print(f"  BACA   : {it['text']}")
                cmd = input("  Enter = mulai rekam | s = lewati | q = keluar : ").strip().lower()
                if cmd == "q":
                    print("Keluar. Rekaman yang tersimpan aman; jalankan lagi untuk melanjutkan.")
                    return
                if cmd == "s":
                    break
                take += 1
                print("  >>> MEREKAM... (tekan Enter untuk berhenti)", end="", flush=True)
                raw, x16, _ = record_ptt(src, dcfg["max_record_s"], dcfg["tail_ms"] / 1000)
                dur = len(x16) / src.out_sr
                peak = dbfs(np.max(np.abs(x16))) if len(x16) else -200.0
                rms = dbfs(np.sqrt(np.mean(x16 ** 2))) if len(x16) else -200.0
                clip = int(np.sum(np.abs(raw) >= lcfg["clip_threshold"]))
                print(f"\n  durasi {dur:.2f} s | puncak {peak:.1f} dBFS | RMS {rms:.1f} dBFS | clipping {clip}")
                warn = []
                if dur < dcfg["min_record_s"]:
                    warn.append("terlalu pendek")
                if peak < dcfg["min_peak_dbfs"]:
                    warn.append("terlalu pelan / mic mati?")
                if clip > 0:
                    warn.append("clipping")
                if warn:
                    print("  PERINGATAN:", ", ".join(warn), "-> disarankan ulang (u)")
                while True:
                    c = input("  Enter = simpan & lanjut | u = ulang | p = putar : ").strip().lower()
                    if c == "p":
                        sd.play(x16, src.out_sr)
                        sd.wait()
                        continue
                    break
                if c == "u":
                    continue
                wav = out_dir / f"{pid}_{it['id']}.wav"
                save_wav(wav, x16, src.out_sr, acfg["wav_subtype"])
                tgt = it.get("target") or it.get("label")
                meta = [r for r in read_csv(meta_p) if not (r["penutur"] == pid and r["item_id"] == it["id"])]
                meta.append({"penutur": pid, "mode": args.mode, "urutan": order.index(i) + 1, "item_id": it["id"],
                             "formality": it["formality"], "intent_target": tgt["intent"],
                             "target_json": json.dumps(tgt, ensure_ascii=False), "teks_baca": it.get("text", ""),
                             "tujuan": it.get("tujuan", ""), "wav": str(wav.relative_to(out_root)).replace("\\", "/"),
                             "durasi_s": round(dur, 3), "peak_dbfs": round(peak, 2), "rms_dbfs": round(rms, 2),
                             "clip_native": clip, "take": take, "waktu": datetime.now().isoformat(timespec="seconds"),
                             "host": host, "perangkat": src.device_name, "hostapi": src.hostapi,
                             "sr_native": src.in_sr, "transkrip": it.get("text", "") if args.mode == "baca" else "",
                             "label_final_json": json.dumps(tgt, ensure_ascii=False) if args.mode == "baca" else "",
                             "status_label": "final (kalimat dibaca)" if args.mode == "baca" else "perlu cek transkrip",
                             "catatan": ";".join(warn)})
                write_csv(meta_p, meta, META_COLS)
                print(f"  tersimpan: {wav.name}")
                break
    print(f"\nSelesai. Metadata: {meta_p}")


if __name__ == "__main__":
    main()
