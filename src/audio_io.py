"""Tahap 1 - Akuisisi mikrofon + downmix mono + resampling ke 16 kHz.

Alur: PortAudio (sounddevice) pada sample rate NATIVE perangkat
      -> blok float32 [frames, ch] -> mono -> soxr.ResampleStream -> 16 kHz.

Perangkat tidak pernah dipaksa membuka 16 kHz; banyak receiver USB hanya
mendukung 44,1/48 kHz. Resampling streaming menjaga state filter antar-blok
sehingga tidak ada artefak di batas blok.
"""
import logging
import queue
import time

import numpy as np
import sounddevice as sd
import soundfile as sf
import soxr

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ perangkat
def list_input_devices():
    """Daftar perangkat yang punya kanal input."""
    devs = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            devs.append({
                "index": i,
                "name": d["name"],
                "hostapi": sd.query_hostapis(d["hostapi"])["name"],
                "channels": d["max_input_channels"],
                "default_samplerate": int(d["default_samplerate"]),
            })
    return devs


def format_device_table(devs):
    lines = [f"{'idx':>3} | {'nama':<50} | {'host API':<20} | ch | sr_native",
             "-" * 95]
    for d in devs:
        lines.append(f"{d['index']:>3} | {d['name'][:50]:<50} | {d['hostapi'][:20]:<20} | "
                     f"{d['channels']:>2} | {d['default_samplerate']}")
    return "\n".join(lines)


def resolve_input_device(device, hostapi=None):
    """Ubah nilai config (None / int / substring nama) menjadi indeks PortAudio."""
    devs = list_input_devices()
    if device is None:
        idx = sd.default.device[0]
        if idx is None or idx < 0:
            raise RuntimeError("Tidak ada perangkat input default.")
        return idx
    if isinstance(device, int):
        if not any(d["index"] == device for d in devs):
            raise ValueError(f"Indeks {device} bukan perangkat input.\n{format_device_table(devs)}")
        return device
    cands = [d for d in devs
             if device.lower() in d["name"].lower()
             and (hostapi is None or hostapi.lower() in d["hostapi"].lower())]
    if not cands:
        raise ValueError(f"Perangkat '{device}' (hostapi={hostapi}) tidak ditemukan.\n"
                         f"{format_device_table(devs)}")
    if len(cands) > 1:
        log.warning("Ada %d perangkat cocok dengan '%s'; dipakai yang pertama: [%d] %s",
                    len(cands), device, cands[0]["index"], cands[0]["name"])
    return cands[0]["index"]


def to_mono(block, channel=None):
    """[frames, ch] -> [frames]. channel=None: rata-rata semua kanal."""
    if block.ndim == 1:
        return block
    if channel is None:
        return block.mean(axis=1, dtype=np.float32)
    return block[:, channel].astype(np.float32, copy=False)


# ------------------------------------------------------------------ sumber audio
class AudioSource:
    """Context manager: stream mikrofon -> blok mono 16 kHz.

    Pemakaian:
        with AudioSource(cfg["audio"]) as src:
            raw, x16 = src.read()
    """

    def __init__(self, audio_cfg):
        self.cfg = audio_cfg
        self.device = resolve_input_device(audio_cfg["device"], audio_cfg.get("hostapi"))
        info = sd.query_devices(self.device)
        self.device_name = info["name"]
        self.hostapi = sd.query_hostapis(info["hostapi"])["name"]
        self.channels = audio_cfg["capture_channels"] or info["max_input_channels"]
        self.in_sr = int(audio_cfg["capture_samplerate"] or info["default_samplerate"])
        self.out_sr = int(audio_cfg["target_samplerate"])
        self.mono_channel = audio_cfg["mono_channel"]
        self.block_frames = int(round(self.in_sr * audio_cfg["block_ms"] / 1000))

        # Validasi: gagal di sini lebih jelas daripada stream error di tengah jalan.
        sd.check_input_settings(device=self.device, channels=self.channels,
                                dtype="float32", samplerate=self.in_sr)

        self._q = queue.Queue(maxsize=audio_cfg["queue_max_blocks"])
        self._resampler = None
        self._stream = None
        self.n_status = 0          # callback melaporkan status (mis. input overflow)
        self.n_dropped = 0         # blok dibuang karena antrean penuh
        self.last_status = None

    # dipanggil di thread PortAudio: harus ringan, tanpa logging/IO
    def _callback(self, indata, frames, time_info, status):
        if status:
            self.n_status += 1
            self.last_status = str(status)
        try:
            self._q.put_nowait(indata.copy())
        except queue.Full:
            self.n_dropped += 1

    def _new_resampler(self):
        if self.in_sr == self.out_sr:
            return None
        return soxr.ResampleStream(self.in_sr, self.out_sr, 1, dtype="float32",
                                   quality=self.cfg["resample_quality"])

    def __enter__(self):
        self._resampler = self._new_resampler()
        self._stream = sd.InputStream(
            samplerate=self.in_sr, blocksize=self.block_frames, device=self.device,
            channels=self.channels, dtype="float32", latency=self.cfg["latency"],
            callback=self._callback)
        self._stream.start()
        log.info("Stream dibuka: [%d] %s (%s) | %d Hz, %d ch, blok %d frame (%.1f ms) "
                 "-> mono %d Hz | latensi PortAudio %.1f ms",
                 self.device, self.device_name, self.hostapi, self.in_sr, self.channels,
                 self.block_frames, 1000 * self.block_frames / self.in_sr, self.out_sr,
                 1000 * self._stream.latency)
        return self

    def __exit__(self, *exc):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self.n_status or self.n_dropped:
            log.warning("Status callback: %d kali (terakhir: %s), blok dibuang: %d",
                        self.n_status, self.last_status, self.n_dropped)
        log.info("Stream ditutup.")

    def read(self, timeout=None):
        """Ambil satu blok. Return (raw_mono @in_sr, mono @out_sr)."""
        block = self._q.get(timeout=timeout)
        mono = to_mono(block, self.mono_channel)
        out = mono if self._resampler is None else self._resampler.resample_chunk(mono)
        return mono, out

    def drain(self):
        """Buang blok yang menumpuk di antrean (mis. selama menunggu input pengguna)
        dan reset resampler, agar rekaman berikutnya mulai dari audio terbaru."""
        n = 0
        while True:
            try:
                self._q.get_nowait()
                n += 1
            except queue.Empty:
                break
        self._resampler = self._new_resampler()
        return n

    def flush(self):
        """Keluarkan sisa sampel di resampler (panggil sekali di akhir rekaman)."""
        if self._resampler is None:
            return np.zeros(0, dtype=np.float32)
        out = self._resampler.resample_chunk(np.zeros(0, dtype=np.float32), last=True)
        self._resampler = self._new_resampler()
        return out

    def record(self, seconds):
        """Rekam `seconds` detik. Return (raw_mono @in_sr, mono @out_sr)."""
        need = int(round(seconds * self.in_sr))
        raw, res = [], []
        got = 0
        t0 = time.perf_counter()
        while got < need:
            r, o = self.read(timeout=2.0 + self.block_frames / self.in_sr)
            raw.append(r)
            res.append(o)
            got += len(r)
        res.append(self.flush())
        log.info("Rekam %.2f s selesai dalam %.2f s (wall clock)", seconds, time.perf_counter() - t0)
        return np.concatenate(raw)[:need], np.concatenate(res)


# ------------------------------------------------------------------ simpan & analisis
def save_wav(path, x, samplerate, subtype):
    sf.write(str(path), x, samplerate, subtype=subtype)
    log.info("WAV disimpan: %s (%d Hz, %s, %.2f s)", path, samplerate, subtype, len(x) / samplerate)


def dbfs(v):
    """Amplitudo linear (full scale = 1.0) -> dBFS. Konvensi: sinus penuh = -3,01 dBFS RMS."""
    return 20.0 * np.log10(max(float(v), 1e-10))


def level_stats(x, samplerate, window_ms, clip_threshold, noise_pct, speech_pct):
    """Statistik level: RMS & peak total, RMS per-jendela (persentil), clipping."""
    win = max(1, int(samplerate * window_ms / 1000))
    n = len(x) // win
    w_rms = np.sqrt(np.mean(x[: n * win].reshape(n, win) ** 2, axis=1)) if n else np.array([0.0])
    clipped = int(np.sum(np.abs(x) >= clip_threshold))
    return {
        "rms_dbfs": dbfs(np.sqrt(np.mean(x ** 2))),
        "peak_dbfs": dbfs(np.max(np.abs(x))),
        f"win_p{noise_pct}_dbfs": dbfs(np.percentile(w_rms, noise_pct)),
        f"win_p{speech_pct}_dbfs": dbfs(np.percentile(w_rms, speech_pct)),
        "clipped_samples": clipped,
        "clipped_pct": 100.0 * clipped / max(1, len(x)),
    }
