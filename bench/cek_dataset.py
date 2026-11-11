"""F8 - Pemeriksaan kualitas rekaman dataset responden (dari WAV + dataset/metadata.csv).

Cek: kelengkapan kartu, format WAV (16 kHz mono PCM_16), durasi, puncak/RMS, clipping native
(dicatat saat rekam), jeda diam awal/akhir (frame 100 ms > -40 dBFS dianggap aktif).
Keluaran: results/kualitas_dataset_<host>_<ts>.{md,json}

Pemakaian:
    python bench/cek_dataset.py
"""
import collections
import io
import csv
import json
import socket
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils import load_config  # noqa: E402


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    cfg = load_config()
    dcfg = cfg["dataset"]
    root = ROOT / dcfg["out_skenario"]
    items = json.load(open(ROOT / dcfg["skenario"], encoding="utf-8"))["items"]
    all_ids = {i["id"] for i in items}
    meta = list(csv.DictReader(open(root / "metadata.csv", encoding="utf-8")))
    resp = list(csv.DictReader(open(root / "responden.csv", encoding="utf-8")))
    sr_native = 48000
    out, lines = {"responden": resp, "per_penutur": {}}, []
    host, ts = socket.gethostname(), datetime.now().strftime("%Y%m%d_%H%M%S")
    lines += [f"# Kualitas rekaman dataset responden ({host}, {ts})", "",
              "| Penutur | n | Hilang | Format salah | Durasi (s) rata-rata ± SD [min–max] | Total (menit) | "
              "Puncak dBFS rata-rata | RMS dBFS rata-rata | File clipping | Sampel clip maks/file | "
              "% sampel clip maks | Take ulang | Diam awal (s) | Diam akhir min (s) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for pid in sorted({m["penutur"] for m in meta}):
        rows = [m for m in meta if m["penutur"] == pid]
        got = {m["item_id"] for m in rows}
        bad, d, s0, s1 = [], [], [], []
        for m in rows:
            p = root / m["wav"]
            x, sr = sf.read(p, dtype="float32")
            if sr != 16000 or x.ndim != 1 or sf.info(p).subtype != "PCM_16":
                bad.append(m["item_id"])
            d.append(len(x) / sr)
            f = x[: len(x) // 1600 * 1600].reshape(-1, 1600)
            e = 20 * np.log10(np.sqrt((f ** 2).mean(1)) + 1e-10)
            act = np.where(e > -40)[0]
            s0.append(act[0] * 0.1 if len(act) else -1)
            s1.append((len(e) - 1 - act[-1]) * 0.1 if len(act) else -1)
        d = np.array(d)
        pk = np.array([float(m["peak_dbfs"]) for m in rows])
        rm = np.array([float(m["rms_dbfs"]) for m in rows])
        cl = np.array([int(m["clip_native"]) for m in rows])
        frac = cl / (np.array([float(m["durasi_s"]) for m in rows]) * sr_native) * 100
        r = {"n": len(rows), "hilang": sorted(all_ids - got), "format_salah": bad,
             "durasi_mean": d.mean(), "durasi_sd": d.std(ddof=1), "durasi_min": d.min(), "durasi_max": d.max(),
             "total_menit": d.sum() / 60, "peak_mean": pk.mean(), "rms_mean": rm.mean(),
             "file_clip": int((cl > 0).sum()), "clip_max": int(cl.max()), "clip_pct_max": float(frac.max()),
             "file_clip_ge50": sorted(m["item_id"] for m, c in zip(rows, cl) if c >= 50),
             "take_ulang": sum(int(m["take"]) > 1 for m in rows), "diam_awal_mean": float(np.mean(s0)),
             "diam_akhir_min": float(min(s1)),
             "formalitas": dict(collections.Counter(m["formality"] for m in rows))}
        out["per_penutur"][pid] = r
        lines.append(f"| {pid} | {r['n']} | {len(r['hilang'])} | {len(bad)} | {r['durasi_mean']:.2f} ± "
                     f"{r['durasi_sd']:.2f} [{r['durasi_min']:.2f}–{r['durasi_max']:.2f}] | {r['total_menit']:.1f} | "
                     f"{r['peak_mean']:.1f} | {r['rms_mean']:.1f} | {r['file_clip']}/{r['n']} | {r['clip_max']} | "
                     f"{r['clip_pct_max']:.3f} | {r['take_ulang']} | {r['diam_awal_mean']:.2f} | "
                     f"{r['diam_akhir_min']:.1f} |")
    lines += ["", "Clipping = jumlah sampel native (48 kHz) dengan |x| ≥ "
              f"{cfg['levels']['clip_threshold']} yang dicatat saat rekam. File dengan ≥ 50 sampel clip: "
              + "; ".join(f"{k}: {', '.join(v['file_clip_ge50']) or '-'}" for k, v in out["per_penutur"].items()),
              "", "Responden: " + "; ".join(f"{r['penutur']} {r['usia']} th {r['jenis_kelamin']} {r['bahasa_ibu']}"
                                           for r in resp)]
    res = ROOT / "results"
    (res / f"kualitas_dataset_{host}_{ts}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (res / f"kualitas_dataset_{host}_{ts}.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n-> results/kualitas_dataset_{host}_{ts}.md")


if __name__ == "__main__":
    main()
