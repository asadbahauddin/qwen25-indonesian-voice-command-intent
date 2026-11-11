"""F3 - ASR Whisper dengan dua backend berantarmuka sama.

    asr = ASR(cfg["asr"], root)            # atau ASR(cfg_asr, root, backend="openai", device="cpu", ...)
    text, info = asr.transcribe(x16)       # x16: float32 mono 16 kHz
    info = {t_asr, audio_s, rtf, backend, model, device, compute, initial_prompt, beam_size}

Backend:
  faster : faster-whisper (CTranslate2), compute_type float16 (cuda) / int8 (cpu)
  openai : openai-whisper (PyTorch), fp16 (cuda) / fp32 (cpu)

CLI cepat:
    python -m src.asr file.wav [--backend openai] [--device cpu] [--tanpa-prompt]
"""
import hashlib
import logging
import time
from pathlib import Path

import numpy as np

log = logging.getLogger("asr")
SR = 16000


def _cuda_available():
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        import torch
        return torch.cuda.is_available()


class ASR:
    def __init__(self, cfg, root, backend=None, model=None, device=None, use_prompt=None, beam_size=None):
        self.cfg = cfg
        self.backend = backend or cfg["backend"]
        self.model_name = model or cfg["model"]
        dev = device or cfg["device"]
        self.device = ("cuda" if _cuda_available() else "cpu") if dev == "auto" else dev
        self.beam_size = beam_size or cfg["beam_size"]
        use_prompt = cfg["use_initial_prompt"] if use_prompt is None else use_prompt
        self.prompt = None
        if use_prompt:
            self.prompt = (Path(root) / cfg["initial_prompt_file"]).read_text(encoding="utf-8").strip()
        self.prompt_sha = hashlib.sha256(self.prompt.encode()).hexdigest()[:12] if self.prompt else None
        t0 = time.perf_counter()
        if self.backend == "faster":
            from faster_whisper import WhisperModel
            self.compute = cfg["compute_type"][self.device]
            self.model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute,
                                      cpu_threads=cfg.get("cpu_threads", 0),
                                      download_root=str(Path(root) / cfg["models_dir"]))
        elif self.backend == "openai":
            import whisper
            self.compute = "float16" if self.device == "cuda" else "float32"
            self.model = whisper.load_model(self.model_name, device=self.device)
        else:
            raise ValueError(f"backend tidak dikenal: {self.backend}")
        self.load_s = time.perf_counter() - t0
        log.info("ASR %s/%s di %s (%s), prompt=%s, beam=%d, load %.2f s", self.backend, self.model_name,
                 self.device, self.compute, self.prompt_sha, self.beam_size, self.load_s)

    def name(self):
        return f"{self.backend}-{self.model_name}-{self.device}-{'prompt' if self.prompt else 'noprompt'}"

    def transcribe(self, x16):
        x16 = np.asarray(x16, dtype=np.float32)
        c = self.cfg
        t0 = time.perf_counter()
        if self.backend == "faster":
            segs, _ = self.model.transcribe(
                x16, language=c["language"], beam_size=self.beam_size, temperature=c["temperature"],
                condition_on_previous_text=c["condition_on_previous_text"], initial_prompt=self.prompt,
                without_timestamps=c["without_timestamps"], vad_filter=False)
            text = " ".join(s.text.strip() for s in segs)   # generator: dekode terjadi di sini
        else:
            r = self.model.transcribe(
                x16, language=c["language"], beam_size=self.beam_size, temperature=c["temperature"],
                condition_on_previous_text=c["condition_on_previous_text"], initial_prompt=self.prompt,
                without_timestamps=c["without_timestamps"], fp16=(self.device == "cuda"), verbose=None)
            text = r["text"]
        dt = time.perf_counter() - t0
        audio_s = len(x16) / SR
        return text.strip(), {"t_asr": dt, "audio_s": audio_s, "rtf": dt / audio_s if audio_s else None,
                              "backend": self.backend, "model": self.model_name, "device": self.device,
                              "compute": self.compute, "initial_prompt": self.prompt_sha,
                              "beam_size": self.beam_size}


if __name__ == "__main__":
    import argparse
    import sys

    import soundfile as sf
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
    from src.utils import load_config
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--backend", choices=["faster", "openai"])
    ap.add_argument("--device", choices=["cuda", "cpu"])
    ap.add_argument("--tanpa-prompt", action="store_true")
    a = ap.parse_args()
    cfg = load_config()
    asr = ASR(cfg["asr"], ROOT, backend=a.backend, device=a.device, use_prompt=False if a.tanpa_prompt else None)
    x, sr = sf.read(a.wav, dtype="float32")
    assert sr == SR and x.ndim == 1, "WAV harus 16 kHz mono"
    asr.transcribe(x)  # pemanasan
    text, info = asr.transcribe(x)
    print(text)
    print(info)
