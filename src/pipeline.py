"""F5 - Pipeline lengkap: audio 16 kHz -> (Silero VAD) -> Whisper -> NLU -> JSON perintah robot.

Komponen dimuat SEKALI lalu dipakai ulang; metode NLU dimuat saat pertama dipakai (lazy).

    pipe = Pipeline(cfg)
    rec = pipe.from_text("tolong ke ruang dosen")                  # NLU saja (teks ground-truth)
    rec = pipe.from_audio(x16, vad_ev=ev)                           # ujaran dari VAD (mode mic)
    rec = pipe.from_file("a.wav", pakai_vad=True)                   # WAV 16 kHz mono

Hasil `rec`: dict {sumber, transkrip, t_vad, t_tunggu_vad, t_asr, asr, hasil: {metode: {json, info, t_total}}}.

Definisi latency (dicatat terpisah, agar tidak tercampur):
  t_vad        = waktu KOMPUTASI Silero untuk frame-frame ujaran itu (tabel laporan kolom "VAD").
  t_tunggu_vad = jeda diam yang ditunggu VAD sebelum menyatakan ujaran selesai (~min_silence;
                 mode file: = min_silence, karena file bisa habis sebelum jeda itu tercapai).
  t_asr, t_nlu = waktu komputasi Whisper dan metode NLU.
  t_total      = t_vad + t_asr + t_nlu   (kolom "Total" tabel laporan; komputasi saja)
  t_respons    = t_tunggu_vad + t_asr + t_nlu  (waktu yang dirasakan pengguna setelah selesai bicara)
"""
import copy
import csv
import json
import logging
import socket
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from src.asr import ASR
from src.nlu.base import Domain
from src.utils import ram_tersedia_gb
from src.vad import SR, SileroVAD, segment_array

ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("pipeline")
METHODS = ["qwen", "rule", "indobert"]

CSV_COLS = ["waktu", "host", "perangkat", "sumber", "file", "metode", "transkrip", "intent", "json",
            "json_valid", "schema_valid", "error", "audio_s", "n_segmen_vad", "t_vad", "t_tunggu_vad",
            "t_asr", "t_nlu", "t_total", "t_respons", "asr", "qwen_load_s", "qwen_prompt_eval_s",
            "qwen_eval_s", "qwen_eval_tokens", "qwen_tokens_per_s", "ram_tersedia_gb"]


class Pipeline:
    def __init__(self, cfg, device=None):
        self.cfg = cfg
        self.pcfg = cfg["pipeline"]
        self.domain = Domain(ROOT / cfg["nlu"]["domain_vocab"])
        self.vad = SileroVAD(cfg["vad"])
        self.device = device or self.pcfg["device"]
        self.whisper = cfg["asr"]["model"]
        self.beam = cfg["asr"]["beam_size"]
        self.asr = None
        self.nlu = {}
        self.host = socket.gethostname()
        self._csv = None

    # ---------------- pemuatan komponen ----------------
    def _cfg_for_device(self):
        c = copy.deepcopy(self.cfg)
        cpu = self.device == "cpu"
        c["asr"]["device"] = "cpu" if cpu else "auto"
        c["nlu"]["indobert"]["device"] = "cpu" if cpu else c["nlu"]["indobert"]["device"]
        c["nlu"]["qwen"]["num_gpu"] = 0 if cpu else self.cfg["nlu"]["qwen"]["num_gpu"]
        return c

    def load_asr(self):
        if self.asr is None:
            c = self._cfg_for_device()["asr"]
            self.asr = ASR(c, ROOT, model=self.whisper, beam_size=self.beam)
            # pemanasan: derau lemah 3 s (diam total membuat Whisper melewatkan dekode -> pemanasan semu)
            rng = np.random.default_rng(0)
            z = (0.01 * rng.standard_normal(3 * SR)).astype(np.float32)
            for _ in range(self.pcfg.get("warmup_runs", 2)):
                self.asr.transcribe(z)
        return self.asr

    def method(self, name):
        if name not in self.nlu:
            c = self._cfg_for_device()
            t0 = time.perf_counter()
            if name == "qwen":
                from src.nlu.qwen import QwenNLU
                m = QwenNLU(c, self.domain)
            elif name == "rule":
                from src.nlu.rule import RuleNLU
                m = RuleNLU(c, self.domain)
            elif name == "indobert":
                from src.nlu.indobert import IndoBertNLU
                m = IndoBertNLU(c, self.domain)
            else:
                raise ValueError(f"metode tidak dikenal: {name}")
            m.warmup()                             # model masuk memori sebelum diukur
            for _ in range(self.pcfg.get("warmup_runs", 2)):   # beban realistis (klausa majemuk)
                m.predict("Tolong ambil berkas di meja lalu antar ke ruang dosen.")
            log.info("metode %s siap (%.2f s termasuk pemanasan)", name, time.perf_counter() - t0)
            self.nlu[name] = m
        return self.nlu[name]

    def set_device(self, device):
        """gpu|cpu: muat ulang Whisper, IndoBERT, dan Qwen (num_gpu) pada perangkat baru."""
        if device == self.device:
            return
        self.device = device
        self.asr = None
        self.nlu = {}
        log.info("perangkat -> %s (komponen dimuat ulang saat dipakai)", device)

    def set_whisper(self, model=None, beam=None):
        if model:
            self.whisper = model
        if beam:
            self.beam = beam
        self.asr = None

    # ---------------- pemrosesan ----------------
    def _nlu_all(self, text, methods):
        out = {}
        for name in methods:
            cmd, info = self.method(name).predict(text)
            out[name] = {"json": cmd, "info": info}
        return out

    def from_text(self, text, methods):
        rec = {"sumber": "teks", "file": "", "transkrip": text, "audio_s": None, "n_segmen_vad": None,
               "t_vad": None, "t_tunggu_vad": None, "t_asr": None, "asr": None}
        rec["hasil"] = self._nlu_all(text, methods)
        self._finish(rec)
        return rec

    def from_audio(self, x16, methods, vad_ev=None, sumber="mic", file=""):
        asr = self.load_asr()
        text, ainfo = asr.transcribe(x16)
        rec = {"sumber": sumber, "file": file, "transkrip": text, "audio_s": len(x16) / SR,
               "n_segmen_vad": 1 if vad_ev else None,
               "t_vad": vad_ev["t_vad"] if vad_ev else None,
               "t_tunggu_vad": vad_ev.get("tunggu_akhir_s") if vad_ev else None,
               "t_asr": ainfo["t_asr"], "asr": asr.name()}
        rec["hasil"] = self._nlu_all(text, methods)
        self._finish(rec)
        return rec

    def from_file(self, path, methods, pakai_vad=True):
        import soundfile as sf
        x, sr = sf.read(str(path), dtype="float32")
        if x.ndim > 1:
            x = x.mean(axis=1)
        if sr != SR:
            raise ValueError(f"{path}: sample rate {sr}, harus {SR} (pakai rekaman dari src/audio_io)")
        ev = None
        if pakai_vad:
            t0 = time.perf_counter()
            segs, _ = segment_array(x, self.cfg["vad"], self.vad)
            t_wall = time.perf_counter() - t0
            if not segs:
                rec = {"sumber": "file", "file": str(path), "transkrip": "", "audio_s": len(x) / SR,
                       "n_segmen_vad": 0, "t_vad": t_wall, "t_tunggu_vad": None, "t_asr": None,
                       "asr": None, "hasil": {}}
                return rec
            # file berisi satu perintah: segmen disambung (sama dengan analisis F2)
            # Jeda tunggu: rekaman file sering habis sebelum diam min_silence tercapai (alasan 'akhir'), sehingga
            # sisa diam di file < jeda yang dialami pengguna. Pada pemakaian langsung VAD selalu menunggu
            # min_silence penuh setelah ucapan terakhir -> itu yang dipakai untuk t_respons.
            ev = {"t_vad": sum(s["t_vad"] for s in segs), "tunggu_akhir_s": self.cfg["vad"]["min_silence_ms"] / 1000}
            x = np.concatenate([s["audio"] for s in segs])
        rec = self.from_audio(x, methods, vad_ev=ev, sumber="file", file=str(path))
        if pakai_vad:
            rec["n_segmen_vad"] = len(segs)
        return rec

    def _finish(self, rec):
        base = sum(v for v in (rec["t_vad"], rec["t_asr"]) if v)
        for name, r in rec["hasil"].items():
            t_nlu = r["info"].get("t_nlu") or 0.0
            r["t_total"] = base + t_nlu
            r["t_respons"] = (rec["t_tunggu_vad"] or 0.0) + (rec["t_asr"] or 0.0) + t_nlu if rec["t_tunggu_vad"] is not None else None
        rec["waktu"] = datetime.now().isoformat(timespec="seconds")
        rec["perangkat"] = self.device
        rec["ram_tersedia_gb"] = ram_tersedia_gb()
        self._log_csv(rec)

    # ---------------- log CSV ----------------
    def _log_csv(self, rec):
        if not self.pcfg.get("csv_log"):
            return
        path = ROOT / f"{self.pcfg['csv_log']}_{self.host}_{datetime.now():%Y%m%d}.csv"
        new = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLS)
            if new:
                w.writeheader()
            for name, r in rec["hasil"].items():
                i = r["info"]
                w.writerow({
                    "waktu": rec["waktu"], "host": self.host, "perangkat": self.device, "sumber": rec["sumber"],
                    "file": rec["file"], "metode": name, "transkrip": rec["transkrip"],
                    "intent": (r["json"] or {}).get("intent") if isinstance(r["json"], dict) else None,
                    "json": json.dumps(r["json"], ensure_ascii=False), "json_valid": i.get("json_valid"),
                    "schema_valid": i.get("schema_valid"), "error": i.get("error"),
                    "audio_s": _r(rec["audio_s"]), "n_segmen_vad": rec["n_segmen_vad"],
                    "t_vad": _r(rec["t_vad"], 5), "t_tunggu_vad": _r(rec["t_tunggu_vad"]),
                    "t_asr": _r(rec["t_asr"], 4), "t_nlu": _r(i.get("t_nlu"), 4), "t_total": _r(r["t_total"], 4),
                    "t_respons": _r(r["t_respons"], 4), "asr": rec["asr"],
                    "qwen_load_s": _r(i.get("load_s"), 4), "qwen_prompt_eval_s": _r(i.get("prompt_eval_s"), 4),
                    "qwen_eval_s": _r(i.get("eval_s"), 4), "qwen_eval_tokens": i.get("eval_tokens"),
                    "qwen_tokens_per_s": _r(i.get("tokens_per_s"), 2),
                    "ram_tersedia_gb": _r(rec["ram_tersedia_gb"], 2)})
        self.csv_path = path


def _r(v, n=3):
    return None if v is None else round(float(v), n)
