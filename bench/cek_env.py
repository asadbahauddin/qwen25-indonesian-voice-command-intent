"""Fase 0 - Pengecekan lingkungan.

Mencetak tabel ringkas: OS, Python, CUDA (nvidia-smi + torch), Ollama,
dan versi pustaka terpasang. Dapat dijalankan ulang di laptop maupun RPi 5.

Pemakaian:
    python bench/cek_env.py
"""
import importlib.metadata as md
import json
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

PACKAGES = [
    "numpy", "scipy", "soxr", "sounddevice", "soundfile", "torch",
    "silero-vad", "onnxruntime", "openai-whisper", "faster-whisper",
    "ctranslate2", "requests", "PyYAML", "jsonschema", "pandas",
]


def run(cmd):
    """Jalankan perintah, kembalikan (ok, stdout+stderr ringkas)."""
    if shutil.which(cmd[0]) is None:
        return False, "tidak ditemukan di PATH"
    # Output ditulis ke file sementara, bukan pipe: di Windows `ollama list`
    # dapat meluncurkan server latar belakang yang mewarisi handle pipe,
    # sehingga capture_output menunggu EOF selamanya (hang).
    try:
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as f:
            p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, text=True, timeout=20)
            f.seek(0)
            return p.returncode == 0, f.read().strip()
    except Exception as e:  # noqa: BLE001
        return False, repr(e)


def check_torch():
    try:
        import torch
    except Exception as e:  # noqa: BLE001
        return {"installed": False, "error": repr(e)}
    info = {
        "installed": True,
        "version": torch.__version__,
        "cuda_build": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
    }
    if info["cuda_available"]:
        info["device"] = torch.cuda.get_device_name(0)
        info["capability"] = "sm_%d%d" % torch.cuda.get_device_capability(0)
        info["cudnn"] = torch.backends.cudnn.version()
    return info


def check_ctranslate2():
    try:
        import ctranslate2
        return {"cuda_devices": ctranslate2.get_cuda_device_count(),
                "compute_types_cuda": sorted(ctranslate2.get_supported_compute_types("cuda"))
                if ctranslate2.get_cuda_device_count() else [],
                "compute_types_cpu": sorted(ctranslate2.get_supported_compute_types("cpu"))}
    except Exception as e:  # noqa: BLE001
        return {"error": repr(e)}


def main():
    rows = []
    rows.append(("OS", f"{platform.system()} {platform.release()} ({platform.version()})"))
    rows.append(("Arsitektur", platform.machine()))
    rows.append(("Hostname", socket.gethostname()))
    rows.append(("Python", f"{platform.python_version()} @ {sys.executable}"))

    ok, out = run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                   "--format=csv,noheader"])
    rows.append(("nvidia-smi", out if ok else f"GAGAL: {out}"))

    t = check_torch()
    if t.get("installed"):
        rows.append(("torch", f"{t['version']} (build CUDA {t['cuda_build']})"))
        rows.append(("torch.cuda.is_available()", str(t["cuda_available"])))
        if t["cuda_available"]:
            rows.append(("GPU (torch)", f"{t['device']} {t['capability']}, cuDNN {t['cudnn']}"))
    else:
        rows.append(("torch", f"BELUM TERPASANG: {t['error']}"))

    c = check_ctranslate2()
    rows.append(("ctranslate2 CUDA", json.dumps(c)))

    ok, out = run(["ollama", "--version"])
    rows.append(("ollama --version", out.replace("\n", " | ")))
    ok, out = run(["ollama", "list"])
    rows.append(("ollama list", out.replace("\n", " | ") if ok else f"GAGAL: {out}"))

    for p in PACKAGES:
        try:
            rows.append((f"pkg {p}", md.version(p)))
        except md.PackageNotFoundError:
            rows.append((f"pkg {p}", "-"))

    w = max(len(k) for k, _ in rows)
    print(f"{'Item'.ljust(w)} | Hasil")
    print(f"{'-' * w}-|-{'-' * 60}")
    for k, v in rows:
        print(f"{k.ljust(w)} | {v}")

    out_dir = Path(__file__).resolve().parents[1] / "results"
    out_dir.mkdir(exist_ok=True)
    fn = out_dir / f"env_{socket.gethostname()}_{datetime.now():%Y%m%d_%H%M%S}.json"
    fn.write_text(json.dumps(dict(rows), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDisimpan ke {fn}")


if __name__ == "__main__":
    main()
