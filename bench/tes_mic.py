"""Fase 1 - Uji mikrofon: daftar perangkat, rekam diam/normal/keras, ukur kualitas.

Untuk tiap kondisi di config `bench.mic_conditions`:
  - rekam `bench.mic_test_seconds` detik dari perangkat di `audio.device`
  - simpan WAV native (mono) dan WAV 16 kHz mono PCM_16 di recordings/
  - level (RMS, peak, persentil RMS per-jendela) dihitung pada sinyal 16 kHz (yang dipakai VAD/ASR)
  - clipping & "sentuh limiter" dihitung pada sinyal NATIVE (keluaran ADC asli); resampling
    dapat menimbulkan overshoot >1.0 pada sinyal mendekati full scale (clipping semu)
SNR (dB) = persentil RMS jendela kondisi ucapan - RMS total rekaman diam.
Jika rekaman diam di bawah `levels.gate_floor_dbfs`, perangkat memakai noise gate dan
SNR tidak merepresentasikan noise ruangan (diberi tanda).
Ringkasan ditulis ke results/mic_<host>_<waktu>.json dan .md.

Pemakaian (di terminal, env mbkm-nlu aktif):
    python bench/tes_mic.py --list               # daftar perangkat input
    python bench/tes_mic.py                      # uji lengkap, tekan Enter sebelum tiap kondisi
    python bench/tes_mic.py --auto               # tanpa Enter, hanya hitung mundur
    python bench/tes_mic.py --from 20261111_222034   # analisis ulang rekaman lama tanpa merekam
"""
import argparse
import json
import logging
import re
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.audio_io import (AudioSource, format_device_table, level_stats,  # noqa: E402
                          list_input_devices, save_wav)
from src.utils import load_config, setup_logging  # noqa: E402

log = logging.getLogger("tes_mic")


def wav_info(path):
    i = sf.info(str(path))
    return {"samplerate": i.samplerate, "channels": i.channels, "subtype": i.subtype,
            "durasi_s": round(i.duration, 3)}


def record_all(cfg, args, host, stamp):
    """Rekam semua kondisi. Return (info perangkat, {kondisi: (path_native, path_16k)}, status stream)."""
    acfg, bcfg = cfg["audio"], cfg["bench"]
    secs, countdown = bcfg["mic_test_seconds"], bcfg["mic_countdown_seconds"]
    rec_dir = cfg["paths"]["recordings"]
    files = {}
    with AudioSource(acfg) as src:
        dev = {"index": src.device, "nama": src.device_name, "hostapi": src.hostapi,
               "samplerate_native": src.in_sr, "channels": src.channels, "samplerate_target": src.out_sr}
        print(f"\nPerangkat: [{src.device}] {src.device_name} ({src.hostapi}), "
              f"{src.in_sr} Hz, {src.channels} ch -> mono {src.out_sr} Hz\n")
        n_status = n_dropped = 0
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
            n_status += src.n_status
            n_dropped += src.n_dropped
            print("    selesai.\n")
            p_nat = rec_dir / f"mic_{name}_{host}_{stamp}_{src.in_sr}.wav"
            p_16k = rec_dir / f"mic_{name}_{host}_{stamp}_16k.wav"
            save_wav(p_nat, raw, src.in_sr, acfg["wav_subtype"])
            save_wav(p_16k, x16, src.out_sr, acfg["wav_subtype"])
            files[name] = (p_nat, p_16k)
    return dev, files, {"callback_status": n_status, "blok_dibuang": n_dropped}


def find_existing(cfg, stamp):
    """Cari WAV hasil rekaman lama berdasarkan cap waktu."""
    rec_dir, files, host = cfg["paths"]["recordings"], {}, None
    for name in cfg["bench"]["mic_conditions"]:
        nat = [p for p in rec_dir.glob(f"mic_{name}_*_{stamp}_*.wav") if not p.name.endswith("_16k.wav")]
        p16 = list(rec_dir.glob(f"mic_{name}_*_{stamp}_16k.wav"))
        if not nat or not p16:
            raise FileNotFoundError(f"WAV kondisi '{name}' dengan cap waktu {stamp} tidak ditemukan di {rec_dir}")
        files[name] = (nat[0], p16[0])
        host = re.match(rf"mic_{name}_(.+)_{stamp}_", p16[0].name).group(1)
    i = sf.info(str(next(iter(files.values()))[0]))
    dev = {"index": None, "nama": "(analisis ulang dari WAV)", "hostapi": None,
           "samplerate_native": i.samplerate, "channels": 1, "samplerate_target": cfg["audio"]["target_samplerate"]}
    return host, dev, files


def analyze(cfg, files):
    lcfg = cfg["levels"]
    stat_args = dict(window_ms=lcfg["window_ms"], clip_threshold=lcfg["clip_threshold"],
                     noise_pct=lcfg["noise_percentile"], speech_pct=lcfg["speech_percentile"])
    out = {}
    for name, (p_nat, p_16k) in files.items():
        x16, sr16 = sf.read(str(p_16k), dtype="float32")
        xn, _ = sf.read(str(p_nat), dtype="float32")
        st = level_stats(x16, sr16, **stat_args)
        clip_n = int(np.sum(np.abs(xn) >= lcfg["clip_threshold"]))
        near_n = int(np.sum(np.abs(xn) >= lcfg["near_full_scale"]))
        st16_clip = st.pop("clipped_samples")
        st.pop("clipped_pct")
        st = {k: round(float(v), 3) for k, v in st.items()}
        out[name] = {"stats_16k": st,
                     "clip_native": clip_n, "clip_native_pct": round(100 * clip_n / max(1, len(xn)), 4),
                     "sentuh_limiter_native": near_n,
                     "overshoot_16k_setelah_resample": st16_clip,
                     "wav_16k": p_16k.name, "wav_native": p_nat.name, "wav_16k_info": wav_info(p_16k)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="tampilkan perangkat input lalu keluar")
    ap.add_argument("--config", default=None, help="path config.yaml (default: root repo)")
    ap.add_argument("--auto", action="store_true", help="jangan tunggu Enter, hanya hitung mundur")
    ap.add_argument("--from", dest="from_stamp", default=None,
                    help="analisis ulang WAV lama dengan cap waktu ini (mis. 20261111_222034)")
    args = ap.parse_args()

    if args.list:
        print(format_device_table(list_input_devices()))
        return

    cfg = load_config(args.config)
    setup_logging(cfg, "tes_mic")
    bcfg, lcfg = cfg["bench"], cfg["levels"]
    sp_key = f"win_p{lcfg['speech_percentile']}_dbfs"

    if args.from_stamp:
        stamp = args.from_stamp
        host, dev, files = find_existing(cfg, stamp)
        stream = {"callback_status": None, "blok_dibuang": None}
        log.info("Analisis ulang rekaman %s", stamp)
    else:
        host, stamp = socket.gethostname(), datetime.now().strftime("%Y%m%d_%H%M%S")
        dev, files, stream = record_all(cfg, args, host, stamp)

    kond = analyze(cfg, files)
    report = {"host": host, "waktu_rekam": stamp, "waktu_analisis": datetime.now().strftime("%Y%m%d_%H%M%S"),
              "perangkat": dev, "config_audio": dict(cfg["audio"]), "config_levels": dict(lcfg),
              "detik_per_kondisi": bcfg["mic_test_seconds"], "kondisi": kond, **stream}

    # SNR
    noise = kond.get("diam", {}).get("stats_16k", {}).get("rms_dbfs")
    snr = {n: round(d["stats_16k"][sp_key] - noise, 2) for n, d in kond.items() if n != "diam"} \
        if noise is not None else {}
    gate = noise is not None and noise < lcfg["gate_floor_dbfs"]
    report["snr_db"] = snr
    report["snr_definisi"] = f"{sp_key}(kondisi) - rms_dbfs(diam), sinyal 16 kHz"
    report["noise_gate_terdeteksi"] = gate

    warn, wcfg = [], bcfg["mic_warn"]
    for n, d in kond.items():
        if d["clip_native"] > 0:
            warn.append(f"'{n}': {d['clip_native']} sampel clipping (native) -> turunkan gain / jauhkan mic")
        info = d["wav_16k_info"]
        if (info["samplerate"], info["channels"], info["subtype"]) != (16000, 1, "PCM_16"):
            warn.append(f"'{n}': format WAV tidak sesuai 16 kHz mono PCM_16: {info}")
    if gate:
        warn.append(f"Rekaman diam {noise} dBFS < {lcfg['gate_floor_dbfs']} dBFS: noise gate perangkat aktif, "
                    "SNR TIDAK mewakili noise ruangan")
    elif "normal" in snr and snr["normal"] < wcfg["min_snr_db"]:
        warn.append(f"SNR normal {snr['normal']} dB < {wcfg['min_snr_db']} dB -> ruangan bising / mic jauh")
    if "normal" in kond and kond["normal"]["stats_16k"]["peak_dbfs"] < wcfg["min_speech_peak_dbfs"]:
        warn.append(f"Puncak ucapan normal < {wcfg['min_speech_peak_dbfs']} dBFS -> terlalu pelan, naikkan gain")
    if stream["callback_status"] or stream["blok_dibuang"]:
        warn.append(f"Stream: status callback {stream['callback_status']}x, blok dibuang {stream['blok_dibuang']}")
    report["peringatan"] = warn

    rows = [[n, d["stats_16k"]["rms_dbfs"], d["stats_16k"]["peak_dbfs"], d["stats_16k"][sp_key],
             d["clip_native"], d["sentuh_limiter_native"], d["overshoot_16k_setelah_resample"]]
            for n, d in kond.items()]
    hdr = ["kondisi", "RMS (dBFS)", "Peak (dBFS)", f"RMS p{lcfg['speech_percentile']} jendela (dBFS)",
           f"clip native (|x|>={lcfg['clip_threshold']})", f"sentuh limiter (|x|>={lcfg['near_full_scale']})",
           "overshoot 16k"]
    table = tabulate(rows, headers=hdr, tablefmt="github")
    snr_txt = ", ".join(f"{k}: {v} dB" for k, v in snr.items()) or "-"
    if gate:
        snr_txt += " (noise gate aktif -> tidak representatif)"
    print(table)
    print(f"\nSNR ({report['snr_definisi']}): {snr_txt}")
    print("Peringatan:" if warn else "Peringatan: tidak ada")
    for w in warn:
        print("  -", w)

    res_dir = cfg["paths"]["results"]
    out_json, out_md = res_dir / f"mic_{host}_{stamp}.json", res_dir / f"mic_{host}_{stamp}.md"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    out_md.write_text(
        f"# Uji mikrofon F1 — {host} — rekam {stamp}\n\n"
        f"Perangkat: {dev['nama']} ({dev['hostapi']}), native {dev['samplerate_native']} Hz "
        f"-> mono {dev['samplerate_target']} Hz; {bcfg['mic_test_seconds']} s per kondisi.\n"
        "Level dihitung pada sinyal 16 kHz; clipping & limiter pada sinyal native.\n\n"
        f"{table}\n\nSNR ({report['snr_definisi']}): {snr_txt}\n\n"
        "Peringatan:\n" + ("\n".join(f"- {w}" for w in warn) or "- tidak ada") + "\n",
        encoding="utf-8")
    print(f"\nRingkasan: {out_md}\nDetail   : {out_json}")
    log.info("Selesai. SNR=%s, gate=%s, peringatan=%d", snr, gate, len(warn))


if __name__ == "__main__":
    main()
