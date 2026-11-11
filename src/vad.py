"""F2 - Segmentasi ujaran real-time dengan Silero VAD + pre-roll.

Silero VAD memberi probabilitas ucapan per frame 512 sampel (32 ms @ 16 kHz). Di atasnya dibuat
state machine:
  DIAM   : frame disimpan di ring buffer pre-roll; bila p >= threshold -> mulai ujaran
           (isi ring buffer ikut diambil, agar awal kata yang lemah tidak terpotong).
  UJARAN : bila p < threshold - neg_offset selama >= min_silence_ms -> ujaran selesai.
           Diam di ekor dipangkas sampai tersisa post_pad_ms. Ujaran < min_speech_ms dibuang (bunyi sesaat).
           Ujaran > max_utterance_s dipotong paksa.

    vad = SileroVAD(cfg["vad"])
    seg = VADSegmenter(cfg["vad"], vad)
    for frame in frames_512:                 # float32 16 kHz
        ev = seg.process(frame)              # None atau dict(audio, start_s, end_s, t_vad, ...)

Offline (simulasi streaming pada satu file): `segment_array(x16, cfg, vad)`.
"""
import logging
import time
from collections import deque

import numpy as np

log = logging.getLogger("vad")
SR = 16000
FRAME = 512


class SileroVAD:
    """Pembungkus model Silero (PyTorch atau ONNX); `prob(frame)` -> float."""

    def __init__(self, cfg):
        import torch
        n_awal = torch.get_num_threads()
        from silero_vad import load_silero_vad   # catatan: silero_vad/model.py memanggil torch.set_num_threads(1) saat import (GLOBAL)
        self.onnx = bool(cfg.get("onnx", False))
        # Mode torch: VAD 1 thread (sesuai config). Mode onnx: sesi onnxruntime silero sudah 1 thread sendiri,
        # jadi thread torch dikembalikan agar komponen lain (IndoBERT di CPU) tidak ikut terkunci 1 thread.
        torch.set_num_threads(cfg.get("threads", 1) if not self.onnx else n_awal)
        t0 = time.perf_counter()
        self.model = load_silero_vad(onnx=self.onnx)
        self.load_s = time.perf_counter() - t0
        self._torch = torch
        log.info("Silero VAD (%s) dimuat %.2f s", "onnx" if self.onnx else "torch", self.load_s)

    def reset(self):
        self.model.reset_states()

    def prob(self, frame):
        with self._torch.no_grad():
            return float(self.model(self._torch.from_numpy(np.ascontiguousarray(frame, dtype=np.float32)), SR))


class VADSegmenter:
    def __init__(self, cfg, vad):
        self.vad = vad
        self.th = cfg["threshold"]
        self.neg = cfg["threshold"] - cfg["neg_offset"]
        fms = FRAME / SR * 1000
        self.pre_n = int(round(cfg["pre_roll_ms"] / fms))
        self.sil_n = int(round(cfg["min_silence_ms"] / fms))
        self.pad_n = int(round(cfg["post_pad_ms"] / fms))
        self.min_speech_n = int(round(cfg["min_speech_ms"] / fms))
        self.max_n = int(cfg["max_utterance_s"] * 1000 / fms)
        self.reset()

    def reset(self):
        self.vad.reset()
        self.ring = deque(maxlen=self.pre_n + 1)
        self.buf, self.active = [], False
        self.sil, self.n_speech, self.frame_i, self.start_i = 0, 0, 0, 0
        self.t_vad = 0.0           # waktu komputasi model sejak awal ujaran berjalan
        self.probs = []

    def _emit(self, reason):
        frames = self.buf[: len(self.buf) - max(0, self.sil - self.pad_n)] if reason == "diam" else self.buf
        ok = self.n_speech >= self.min_speech_n
        ev = None
        if ok:
            audio = np.concatenate(frames)
            ev = {"audio": audio, "start_s": self.start_i * FRAME / SR,
                  "end_s": (self.start_i + len(frames)) * FRAME / SR, "durasi_s": len(audio) / SR,
                  "alasan": reason, "t_vad": self.t_vad, "n_frame_ucapan": self.n_speech,
                  "tunggu_akhir_s": self.sil * FRAME / SR}
        self.buf, self.active, self.sil, self.n_speech = [], False, 0, 0
        self.ring.clear()
        self.t_vad = 0.0
        return ev

    def process(self, frame):
        """Masukkan tepat 1 frame (512 sampel). Return dict ujaran saat selesai, selain itu None."""
        t0 = time.perf_counter()
        p = self.vad.prob(frame)
        self.t_vad += time.perf_counter() - t0
        self.probs.append(p)
        i = self.frame_i
        self.frame_i += 1
        if not self.active:
            self.ring.append(frame)
            if p >= self.th:
                self.active = True
                self.buf = list(self.ring)
                self.start_i = i - len(self.ring) + 1
                self.n_speech, self.sil = 1, 0
                self.t_vad = time.perf_counter() - t0   # hitung komputasi mulai dari awal ujaran
            return None
        self.buf.append(frame)
        if p >= self.th:
            self.n_speech += 1
            self.sil = 0
        elif p < self.neg:
            self.sil += 1
        else:                       # zona histeresis: tidak dihitung ucapan maupun diam
            pass
        if self.sil >= self.sil_n:
            return self._emit("diam")
        if len(self.buf) >= self.max_n:
            return self._emit("maks")
        return None

    def flush(self):
        """Akhir aliran: keluarkan ujaran yang masih aktif (alasan 'akhir')."""
        return self._emit("akhir") if self.active else None


def frames_of(x16):
    n = len(x16) // FRAME
    return [x16[k * FRAME:(k + 1) * FRAME] for k in range(n)]


def segment_array(x16, cfg, vad):
    """Simulasi streaming pada seluruh array. Return (daftar ujaran, probabilitas per frame)."""
    seg = VADSegmenter(cfg, vad)
    out = []
    for f in frames_of(np.asarray(x16, dtype=np.float32)):
        ev = seg.process(f)
        if ev:
            out.append(ev)
    ev = seg.flush()
    if ev:
        out.append(ev)
    return out, seg.probs
