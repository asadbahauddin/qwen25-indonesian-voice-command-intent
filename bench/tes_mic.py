"""Fase 1 - Uji mikrofon: daftar perangkat, rekam diam/normal/keras, ukur kualitas.

Untuk tiap kondisi di config `bench.mic_conditions`:
  - rekam `bench.mic_test_seconds` detik dari perangkat di `audio.device`
  - simpan WAV native (mono) dan WAV 16 kHz mono PCM_16 di recordings/
  - hitung RMS, peak, persentil RMS per-jendela, jumlah sampel clipping
Lalu SNR (dB) = level ucapan (persentil RMS jendela) - noise floor (RMS rekaman diam).
Ringkasan ditulis ke results/mic_<host>_<waktu>.json dan .md.

Pemakaian (di terminal, env mbkm-nlu aktif):
    python bench/tes_mic.py --list        # daftar perangkat input
    python bench/tes_mic.py               # uji lengkap, tekan Enter sebelum tiap kondisi
    python bench/tes_mic.py --auto        # tanpa Enter, hanya hitung mundur
"""
import argparse
import json
import logging
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

import soundfile as sf
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.audio_io import (AudioSource, dbfs, format_device_table,  # noqa: E402
                          level_stats, list_input_devices, save_wav)
from src.utils import load_config, setup_logging  # noqa: E402

log = logging.getLogger("tes_mic")


def wav_info(path):
    i = sf.info(str(path))
    return {"samplerate": i.samplerate, "channels": i.channels, "subtype": i.subtype,
            "durasi_s": round(i.duration, 3)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="tampilkan perangkat input lalu keluar")
    ap.add_argument("--config", default=None, help="path config.yaml (default: root repo)")
    ap.add_argument("--auto", action="store_true", help="jangan tunggu Enter, hanya hitung mundur")
    args = ap.parse_args()

    if args.list:
        print(format_device_table(list_input_devices()))
        return

    cfg = load_config(args.config)
    setup_logging(cfg, "tes_mic")
    acfg, bcfg, lcfg = cfg["audio"], cfg["bench"], cfg["levels"]
    secs, countdown = bcfg["mic_test_seconds"], bcfg["mic_countdown_seconds"]
    host, stamp = socket.gethostname(), datetime.now().strftime("%Y%m%d_%H%M%S")
    rec_dir, res_dir = cfg["paths"]["recordings"], cfg["paths"]["results"]
    stat_args = dict(window_ms=lcfg["window_ms"], clip_threshold=lcfg["clip_threshold"],
                     noise_pct=lcfg["noise_percentile"], speech_pct=lcfg["speech_percentile"])
    sp_key = f"win_p{lcfg['speech_percentile']}_dbfs"

    rows, report = [], {"host": host, "waktu": stamp, "config": {k: acfg[k] for k in acfg},
                        "detik_per_kondisi": secs, "kondisi": {}}
    with AudioSource(acfg) as src:
        report["perangkat"] = {"index": src.device, "nama": src.device_name, "hostapi": src.hostapi,
                               "samplerate_native": src.in_sr, "channels": src.channels,
                               "samplerate_target": src.out_sr}
        print(f"\nPerangkat: [{src.device}] {src.device_name} ({src.hostapi}), "
              f"{src.in_sr} Hz, {src.channels} ch -> mono {src.out_sr} Hz\n")
        for name, instr in bcfg["mic_conditions"].items():
            print(f"=== Kondisi '{name}': {instr} ({secs} s)")
            if not args.auto:
                input("    Tekan Enter jika siap...")
            for c in range(countdown, 0, -1):
                print(f"    {c}...", flush=True)
                time.sleep(1)
            src.drain()   # buang audio yang menumpuk selama menunggu Enter / hitung mundur
            print("    >>> REKAM", flush=True)
            raw, x16 = src.record(secs)
            print("    selesai.\n")

            p_nat = rec_dir / f"mic_{name}_{host}_{stamp}_{src.in_sr}.wav"
            p_16k = rec_dir / f"mic_{name}_{host}_{stamp}_16k.wav"
            save_wav(p_nat, raw, src.in_sr, acfg["wav_subtype"])
            save_wav(p_16k, x16, src.out_sr, acfg["wav_subtype"])
            st = level_stats(x16, src.out_sr, **stat_args)
            st = {k: round(v, 3) if isinstance(v, float) else v for k, v in st.items()}
            report["kondisi"][name] = {"stats_16k": st, "wav_16k": p_16k.name, "wav_native": p_nat.name,
                                       "wav_16k_info": wav_info(p_16k)}
            rows.append([name, st["rms_dbfs"], st["peak_dbfs"], st[sp_key], st["clipped_samples"],
                         f"{st['clipped_pct']:.4f}"])
        report["callback_status"] = src.n_status
        report["blok_dibuang"] = src.n_dropped

    # SNR: level ucapan (persentil RMS jendela) dibanding RMS total rekaman diam
    noise = report["kondisi"].get("diam", {}).get("stats_16k", {}).get("rms_dbfs")
    snr = {}
    if noise is not None:
        for name, d in report["kondisi"].items():
            if name != "diam":
                snr[name] = round(d["stats_16k"][sp_key] - noise, 2)
    report["snr_db"] = snr
    report["snr_definisi"] = f"{sp_key}(kondisi) - rms_dbfs(diam), dihitung pada sinyal 16 kHz"

    warn = []
    wcfg = bcfg["mic_warn"]
    for name, d in report["kondisi"].items():
        if d["stats_16k"]["clipped_samples"] > 0:
            warn.append(f"'{name}': {d['stats_16k']['clipped_samples']} sampel clipping -> turunkan gain mic")
        info = d["wav_16k_info"]
        if (info["samplerate"], info["channels"], info["subtype"]) != (16000, 1, "PCM_16"):
            warn.append(f"'{name}': format WAV tidak sesuai 16 kHz mono PCM_16: {info}")
    if "normal" in snr and snr["normal"] < wcfg["min_snr_db"]:
        warn.append(f"SNR normal {snr['normal']} dB < {wcfg['min_snr_db']} dB -> ruangan bising / mic jauh")
    if "normal" in report["kondisi"] and \
            report["kondisi"]["normal"]["stats_16k"]["peak_dbfs"] < wcfg["min_speech_peak_dbfs"]:
        warn.append(f"Puncak ucapan normal < {wcfg['min_speech_peak_dbfs']} dBFS -> terlalu pelan, naikkan gain")
    if report["callback_status"] or report["blok_dibuang"]:
        warn.append(f"Stream: status callback {report['callback_status']}x, blok dibuang {report['blok_dibuang']}")
    report["peringatan"] = warn

    hdr = ["kondisi", "RMS (dBFS)", "Peak (dBFS)", f"RMS p{lcfg['speech_percentile']} jendela (dBFS)",
           "clip (sampel)", "clip (%)"]
    table = tabulate(rows, headers=hdr, tablefmt="github")
    snr_txt = ", ".join(f"{k}: {v} dB" for k, v in snr.items()) or "-"
    print(table)
    print(f"\nSNR ({report['snr_definisi']}): {snr_txt}")
    print("Peringatan:" if warn else "Peringatan: tidak ada")
    for w in warn:
        print("  -", w)

    out_json = res_dir / f"mic_{host}_{stamp}.json"
    out_md = res_dir / f"mic_{host}_{stamp}.md"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    p = report["perangkat"]
    out_md.write_text(
        f"# Uji mikrofon F1 — {host} — {stamp}\n\n"
        f"Perangkat: [{p['index']}] {p['nama']} ({p['hostapi']}), {p['samplerate_native']} Hz, "
        f"{p['channels']} ch -> mono {p['samplerate_target']} Hz; {secs} s per kondisi.\n\n"
        f"{table}\n\nSNR ({report['snr_definisi']}): {snr_txt}\n\n"
        "Peringatan:\n" + ("\n".join(f"- {w}" for w in warn) or "- tidak ada") + "\n",
        encoding="utf-8")
    print(f"\nRingkasan: {out_md}\nDetail   : {out_json}")
    log.info("Selesai. SNR=%s, peringatan=%d", snr, len(warn))


if __name__ == "__main__":
    main()
