"""F5 - CLI interaktif pipeline perintah suara -> JSON robot.

Model dimuat sekali; semua pengaturan diganti tanpa restart Python.

    python -m src.cli                 # mulai sesuai config.yaml: pipeline
    python -m src.cli --mode mic --metode semua

Perintah (ketik lalu Enter):
  /metode qwen|rule|indobert|semua   metode NLU aktif (boleh lebih dari satu: /metode qwen rule)
  /mode mic|teks                     sumber masukan: mikrofon (VAD) atau ketik kalimat
  /whisper base|small [--unduh]      ganti model Whisper (small perlu diunduh dulu, ~480 MB)
  /beam <n>                          beam size Whisper
  /perangkat gpu|cpu                 skenario laptop GPU atau laptop CPU (Whisper int8, Qwen num_gpu 0)
  /file <wav>                        proses satu file WAV 16 kHz (melalui VAD)
  /stat                              rata-rata ± SD latency sesi ini
  /reset                             kosongkan statistik
  /simpan                            simpan ringkasan sesi ke results/cli_<host>_<ts>.{md,json}
  /bantuan                           daftar perintah
  /keluar                            keluar
Selain perintah: pada mode teks, kalimat yang diketik langsung diproses (juga bisa saat mode mic).
"""
import argparse
import json
import queue
import statistics as st
import sys
import threading
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path

import numpy as np
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.audio_io import AudioSource, save_wav  # noqa: E402
from src.pipeline import METHODS, Pipeline  # noqa: E402
from src.utils import load_config, ram_tersedia_gb, setup_logging  # noqa: E402
from src.vad import FRAME, VADSegmenter  # noqa: E402

con = Console()
KOLOM = ["t_vad", "t_asr", "t_nlu", "t_total", "t_respons"]


def suhu_cpu():
    """Suhu CPU (°C) bila tersedia (Linux/RPi: thermal_zone0). Windows: None."""
    p = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        return int(p.read_text().strip()) / 1000
    except Exception:
        return None


def fmt(v, n=3):
    return "–" if v is None else f"{v:.{n}f}"


class CLI:
    def __init__(self, cfg, a):
        self.cfg = cfg
        self.pipe = Pipeline(cfg, device=a.perangkat)
        self.methods = METHODS if a.metode == ["semua"] else (a.metode or list(cfg["pipeline"]["methods"]))
        self.mode = a.mode or cfg["pipeline"]["mode"]
        self.stats = {}
        self.n_proses = 0
        self.lines = queue.Queue()
        self.stop = False

    # ---------------- tampilan ----------------
    def status(self):
        s = suhu_cpu()
        con.print(f"[bold]metode[/]={','.join(self.methods)}  [bold]mode[/]={self.mode}  "
                  f"[bold]whisper[/]={self.pipe.whisper} beam {self.pipe.beam}  "
                  f"[bold]perangkat[/]={self.pipe.device}" + (f"  [bold]suhu CPU[/]={s:.1f} °C" if s else "")
                  + (f"  [bold]RAM tersedia[/]={r:.1f} GB" if (r := ram_tersedia_gb()) else ""))

    def show(self, rec):
        if rec["sumber"] != "teks":
            extra = f"  (audio {rec['audio_s']:.2f} s, {rec['asr']})" if rec["audio_s"] else ""
            con.print(Panel(rec["transkrip"] or "[i](kosong)[/]", title="Transkrip Whisper" + extra,
                            title_align="left"))
        t = Table(title="Latency (detik)", title_justify="left")
        for c in ["metode", "json_valid", "intent", *KOLOM, "load", "prompt_eval", "eval", "tok/s"]:
            t.add_column(c, justify="right" if c.startswith(("t_", "load", "prompt", "eval", "tok")) else "left")
        for name, r in rec["hasil"].items():
            i = r["info"]
            ok = i.get("json_valid") and i.get("schema_valid", True)
            con.print(Panel(JSON(json.dumps(r["json"], ensure_ascii=False)) if r["json"] is not None
                            else f"[red]{i.get('error')}[/]", title=f"{name}", title_align="left",
                            border_style="green" if ok else "red"))
            t.add_row(name, "[green]ya[/]" if ok else f"[red]tidak[/] {i.get('error') or ''}",
                      str((r["json"] or {}).get("intent") if isinstance(r["json"], dict) else None),
                      fmt(rec["t_vad"], 4), fmt(rec["t_asr"]), fmt(i.get("t_nlu")), fmt(r["t_total"]),
                      fmt(r["t_respons"]), fmt(i.get("load_s")), fmt(i.get("prompt_eval_s")),
                      fmt(i.get("eval_s")), fmt(i.get("tokens_per_s"), 1))
            d = self.stats.setdefault((self.pipe.device, rec["sumber"] != "teks", name), {k: [] for k in KOLOM})
            for k, v in [("t_vad", rec["t_vad"]), ("t_asr", rec["t_asr"]), ("t_nlu", i.get("t_nlu")),
                         ("t_total", r["t_total"]), ("t_respons", r["t_respons"])]:
                if v is not None:
                    d[k].append(v)
        con.print(t)
        self.status()

    def stat_table(self):
        t = Table(title="Statistik sesi: rata-rata ± SD (n)", title_justify="left")
        for c in ["perangkat", "masukan", "metode", *KOLOM]:
            t.add_column(c)
        for (dev, audio, name), d in sorted(self.stats.items()):
            t.add_row(dev, "audio" if audio else "teks", name, *[ms(d[k]) for k in KOLOM])
        return t

    # ---------------- perintah ----------------
    def command(self, line):
        p = line.split()
        c, args = p[0].lower(), p[1:]
        if c in ("/keluar", "/exit", "/quit"):
            self.stop = True
        elif c == "/bantuan":
            con.print(__doc__.split("Perintah")[1])
        elif c == "/metode":
            m = METHODS if args == ["semua"] else args
            bad = [x for x in m if x not in METHODS]
            if not m or bad:
                con.print(f"[red]metode tidak dikenal: {bad or '(kosong)'}[/]  pilihan: {METHODS} | semua")
                return
            self.methods = m
            for x in m:
                with con.status(f"memuat {x}..."):
                    self.pipe.method(x)
        elif c == "/mode":
            if args and args[0] in ("mic", "teks"):
                self.mode = args[0]
            else:
                con.print("[red]/mode mic|teks[/]")
        elif c == "/whisper":
            if not args or args[0] not in self.cfg["pipeline"]["whisper_allowed"]:
                con.print(f"[red]/whisper {'|'.join(self.cfg['pipeline']['whisper_allowed'])}[/]")
                return
            m = args[0]
            lokal = (ROOT / self.cfg["asr"]["models_dir"] / f"models--Systran--faster-whisper-{m}").exists()
            if self.cfg["asr"]["backend"] == "faster" and not lokal and "--unduh" not in args:
                con.print(f"[yellow]Model {m} belum ada di {self.cfg['asr']['models_dir']}. "
                          f"Perlu diunduh dari internet. Ulangi dengan: /whisper {m} --unduh[/]")
                return
            self.pipe.set_whisper(model=m)
            with con.status(f"memuat Whisper {m}..."):
                self.pipe.load_asr()
        elif c == "/beam":
            try:
                self.pipe.set_whisper(beam=int(args[0]))
                with con.status("memuat ulang Whisper..."):
                    self.pipe.load_asr()
            except (IndexError, ValueError):
                con.print("[red]/beam <angka>[/]")
        elif c == "/perangkat":
            if not args or args[0] not in ("gpu", "cpu"):
                con.print("[red]/perangkat gpu|cpu[/]")
                return
            self.pipe.set_device(args[0])
            with con.status(f"memuat ulang komponen di {args[0]} (Qwen dimuat ulang oleh Ollama)..."):
                self.pipe.load_asr()
                for x in self.methods:
                    self.pipe.method(x)
        elif c == "/file":
            if not args or not Path(" ".join(args)).exists():
                con.print("[red]/file <path wav> (file tidak ditemukan)[/]")
                return
            self.show(self.pipe.from_file(" ".join(args), self.methods))
            return
        elif c == "/stat":
            con.print(self.stat_table())
            return
        elif c == "/reset":
            self.stats = {}
            con.print("statistik dikosongkan.")
        elif c == "/simpan":
            self.simpan()
            return
        else:
            con.print(f"[red]perintah tidak dikenal: {c}[/] (/bantuan)")
            return
        self.status()

    def simpan(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        host = self.pipe.host
        out = self.cfg["paths"]["results"] / f"cli_{host}_{ts}"
        rows = [{"perangkat": d, "masukan": "audio" if a else "teks", "metode": n,
                 **{k: summ(v[k]) for k in KOLOM}} for (d, a, n), v in sorted(self.stats.items())]
        meta = {"host": host, "waktu": ts, "whisper": self.pipe.whisper, "beam": self.pipe.beam,
                "asr_backend": self.cfg["asr"]["backend"], "vad": self.cfg["vad"],
                "qwen": {k: self.cfg["nlu"]["qwen"][k] for k in ("model", "prompt_version", "schema_version")},
                "csv_log": str(getattr(self.pipe, "csv_path", "")), "statistik": rows}
        out.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        md = [f"# Ringkasan sesi CLI — {host} {ts}", "",
              f"Whisper {self.pipe.whisper} ({self.cfg['asr']['backend']}), beam {self.pipe.beam}. "
              f"Log per ujaran: `{Path(meta['csv_log']).name}`.", "",
              "Latency dalam detik, rata-rata ± SD (n). t_total = VAD + Whisper + NLU (komputasi). "
              "t_respons = jeda tunggu VAD + Whisper + NLU.", "",
              "| Perangkat | Masukan | Metode | " + " | ".join(KOLOM) + " |",
              "|" + "---|" * (3 + len(KOLOM))]
        for (d, a, n), v in sorted(self.stats.items()):
            md.append(f"| {d} | {'audio' if a else 'teks'} | {n} | " + " | ".join(ms(v[k]) for k in KOLOM) + " |")
        out.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
        con.print(f"tersimpan: {out.with_suffix('.md').relative_to(ROOT)} (+ .json)")

    # ---------------- loop utama ----------------
    def reader(self):
        while True:
            try:
                self.lines.put(input())
            except EOFError:
                self.lines.put("/keluar")
                return

    def handle_line(self, line):
        line = line.strip()
        if not line:
            return
        if line.startswith("/"):
            self.command(line)
        else:
            self.show(self.pipe.from_text(line, self.methods))
        self.n_proses += 1

    def run(self):
        with con.status("memuat Silero VAD, Whisper, dan metode NLU..."):
            self.pipe.load_asr()
            for x in self.methods:
                self.pipe.method(x)
        con.print(Panel("Pipeline siap. /bantuan untuk daftar perintah. "
                        "Mode teks: ketik perintah. Mode mic: bicara saja.", title="CLI MBKM"))
        self.status()
        threading.Thread(target=self.reader, daemon=True).start()
        rec_dir = self.cfg["paths"]["recordings"] / "cli"
        with ExitStack() as stack:
            src = seg = None
            pend = np.zeros(0, np.float32)
            while not self.stop:
                if self.mode == "mic" and src is None:
                    try:
                        src = stack.enter_context(AudioSource(self.cfg["audio"]))
                    except Exception as e:      # receiver tidak tercolok, perangkat sibuk, dll.
                        con.print(f"[red]Mikrofon tidak bisa dibuka: {str(e).splitlines()[0]}[/]\n"
                                  "Cek receiver USB tercolok, lalu /mode mic lagi. Kembali ke mode teks.")
                        self.mode = "teks"
                        continue
                    seg = VADSegmenter(self.cfg["vad"], self.pipe.vad)
                    con.print(f"[cyan]Mendengarkan: {src.device_name} ({src.in_sr} Hz -> 16 kHz)[/]")
                elif self.mode == "teks" and src is not None:
                    stack.close()
                    src = seg = None
                    con.print("[cyan]Mikrofon ditutup (mode teks).[/]")
                if self.mode == "teks":
                    try:
                        self.handle_line(self.lines.get(timeout=0.5))
                    except queue.Empty:
                        pass
                    continue
                # mode mic
                try:
                    self.handle_line(self.lines.get_nowait())
                    continue
                except queue.Empty:
                    pass
                _, x = src.read(timeout=2.0)
                pend = np.concatenate([pend, x])
                while len(pend) >= FRAME:
                    f, pend = pend[:FRAME], pend[FRAME:]
                    ev = seg.process(f)
                    if ev:
                        con.print(f"[cyan]ujaran {ev['durasi_s']:.2f} s ({ev['alasan']})[/]")
                        fname = ""
                        if self.cfg["pipeline"]["save_audio"]:
                            rec_dir.mkdir(parents=True, exist_ok=True)
                            wav = rec_dir / f"cli_{datetime.now():%Y%m%d_%H%M%S}.wav"
                            save_wav(wav, ev["audio"], 16000, self.cfg["audio"]["wav_subtype"])
                            fname = str(wav.relative_to(ROOT))
                        self.show(self.pipe.from_audio(ev["audio"], self.methods, vad_ev=ev, file=fname))
                        src.drain()            # buang audio yang menumpuk selama pemrosesan
                        seg.reset()
                        pend = np.zeros(0, np.float32)
                        break
        con.print("Selesai.")


def summ(v):
    if not v:
        return None
    return {"n": len(v), "mean": st.mean(v), "sd": st.stdev(v) if len(v) > 1 else 0.0}


def ms(v):
    if not v:
        return "–"
    return f"{st.mean(v):.3f} ± {st.stdev(v) if len(v) > 1 else 0:.3f} ({len(v)})"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["mic", "teks"])
    ap.add_argument("--metode", nargs="+", choices=[*METHODS, "semua"])
    ap.add_argument("--perangkat", choices=["gpu", "cpu"])
    ap.add_argument("--mic", help="ganti perangkat input (substring nama), mis. 'Microphone Array' (uji tanpa receiver)")
    a = ap.parse_args()
    import os
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    try:
        from transformers.utils import logging as hf_logging
        hf_logging.disable_progress_bar()       # bilah "Loading weights" mengganggu tampilan rich
    except Exception:
        pass
    cfg = load_config()
    setup_logging(cfg, "cli")
    if a.mic:
        cfg["audio"]["device"] = a.mic
    import logging
    for h in logging.getLogger().handlers:      # konsol bersih untuk rich; log lengkap tetap ke file
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            h.setLevel(logging.WARNING)
    CLI(cfg, a).run()


if __name__ == "__main__":
    main()
