"""Tangkapan layar CLI asli: menjalankan src/cli.py (bukan tiruan) dengan masukan pilot (set pengembangan,
bukan data responden), merekam tampilan terminal rich, lalu merendernya ke PNG dengan Edge headless.

    python luaran/tangkapan_cli.py
Keluaran: luaran/tangkapan/*.svg dan *.png + keterangan.txt
"""
import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rich.console import Console  # noqa: E402

import src.cli as cli_mod  # noqa: E402
from src.utils import load_config, setup_logging  # noqa: E402

OUT = ROOT / "luaran" / "tangkapan"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PILOT = ROOT / "recordings" / "pilot_audio" / "P01"


def shot(con, name, title, ket):
    svg = OUT / f"{name}.svg"
    con.save_svg(str(svg), title=title)
    s = svg.read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s)
    w, h = int(float(m.group(1))) + 4, int(float(m.group(2))) + 4
    png = OUT / f"{name}.png"
    html = OUT / f"{name}.html"
    html.write_text(f'<html><body style="margin:0;background:#fff">{s}</body></html>', encoding="utf-8")
    subprocess.run([EDGE, "--headless", "--disable-gpu", "--hide-scrollbars", f"--screenshot={png}",
                    f"--window-size={w},{h}", "--force-device-scale-factor=2", html.as_uri()],
                   check=True, capture_output=True, timeout=120)
    html.unlink()
    print(f"{png.name} ({w}x{h})")
    return f"{png.name}: {ket}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    setup_logging(cfg, "tangkapan_cli")
    for h in logging.getLogger().handlers:
        if type(h) is logging.StreamHandler:
            h.setLevel(logging.ERROR)
    try:
        from transformers.utils import logging as hf
        hf.disable_progress_bar()
    except Exception:
        pass
    cfg["pipeline"]["csv_log"] = None
    con = Console(record=True, width=120, force_terminal=True, color_system="truecolor")
    cli_mod.con = con                      # CLI asli, tampilan direkam
    a = argparse.Namespace(mode="teks", metode=["semua"], perangkat="gpu", mic=None)
    app = cli_mod.CLI(cfg, a)
    app.pipe.load_asr()
    for m in app.methods:
        app.pipe.method(m)
    ket = []

    con.print(cli_mod.Panel("Pipeline siap. /bantuan untuk daftar perintah. Mode teks: ketik perintah. Mode mic: bicara saja.",
                            title="CLI MBKM"))
    app.status()
    con.print("> /bantuan")
    app.command("/bantuan")
    ket.append(shot(con, "01_mulai_bantuan", "CLI MBKM — mulai dan /bantuan",
                    "Tampilan awal CLI: status metode/mode/Whisper/perangkat dan daftar perintah (/metode, /mode, /whisper, /beam, /perangkat, /file, /stat, /reset, /simpan)."))

    teks = "Silakan temukan Ibu Vivi."
    con.print(f"> {teks}")
    app.handle_line(teks)
    ket.append(shot(con, "02_mode_teks", "CLI MBKM — mode teks, tiga metode",
                    f"Mode teks: kalimat pilot \"{teks}\" diproses ketiga metode; JSON per metode dan tabel latency (t_nlu, load/prompt_eval/eval, token/s)."))

    wav = PILOT / "P01_P26.wav"
    con.print(f"> /file {wav.relative_to(ROOT)}")
    app.command(f"/file {wav}")
    ket.append(shot(con, "03_file_audio_gpu", "CLI MBKM — audio pilot, laptop GPU",
                    "Masukan audio (rekaman pilot P26, perintah majemuk) melalui VAD → Whisper → tiga metode NLU di laptop GPU: transkrip, JSON, latency per tahap."))

    con.print("> /perangkat cpu")
    app.command("/perangkat cpu")
    con.print(f"> /file {wav.relative_to(ROOT)}")
    app.command(f"/file {wav}")
    con.print("> /stat")
    app.command("/stat")
    ket.append(shot(con, "04_cpu_stat", "CLI MBKM — laptop CPU dan /stat",
                    "Pindah ke laptop CPU tanpa restart (/perangkat cpu), audio yang sama diproses ulang, lalu /stat menampilkan rata-rata ± SD latency sesi."))
    (OUT / "keterangan.txt").write_text("\n".join(ket) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
