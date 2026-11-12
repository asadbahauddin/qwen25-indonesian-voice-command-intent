"""Poster ilmiah A1 tegak (HTML -> PDF lewat Edge headless). Angka dibaca dari results/ (bukan diketik).

    python luaran/buat_poster.py
Keluaran: luaran/poster/poster.html, poster.pdf, poster_pratinjau.png
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "luaran" / "poster"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
EV = json.load(open(ROOT / "results" / "eval_dataset_MSI_20261112_095743.json", encoding="utf-8"))
AN = json.load(open(ROOT / "results" / "analisis_dataset_MSI_20261112_104423.json", encoding="utf-8"))
f = lambda x, d=1: f"{x:.{d}f}".replace(".", ",")
acc = lambda dev, mk, m, k="intent_acc": EV["akurasi"][f"{dev}/{mk}/{m}"]["semua"][k] * 100
lat = lambda dev, k: EV["latency"][f"{dev}/vad/qwen"][k]
wer_vad = EV["wer"]["gpu/vad"]["semua"]["wer"] * 100
comb = AN["per_intent"]["gpu/teks"]["qwen"]["combined_command"]
G = "../gambar/"

html = f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Poster MBKM</title><style>
@page {{ size: 594mm 841mm; margin: 0; }}
:root {{ --biru:#0b3d91; --biru2:#1f5fbf; --kuning:#f2b705; --teks:#1b1f24; --abu:#5b6470; --latar:#f4f6fa; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; width:594mm; height:841mm; font-family:"Segoe UI", Arial, sans-serif; color:var(--teks); background:#fff; }}
header {{ background:var(--biru); color:#fff; padding:14mm 18mm 12mm; display:flex; gap:12mm; align-items:center; border-bottom:4mm solid var(--kuning); }}
header img {{ width:40mm; height:auto; background:#fff; border-radius:3mm; padding:2mm; }}
h1 {{ font-size:23pt*0; margin:0; }}
.judul {{ font-size:34pt; font-weight:800; line-height:1.15; margin:0 0 4mm; }}
.penulis {{ font-size:19pt; font-weight:600; margin:0; }}
.afil {{ font-size:15pt; opacity:.9; margin:2mm 0 0; }}
main {{ padding:10mm 14mm 0; display:grid; grid-template-columns: 1fr 1fr; gap:9mm; }}
section {{ background:var(--latar); border-radius:4mm; padding:7mm 8mm; }}
h2 {{ font-size:22pt; color:var(--biru); margin:0 0 4mm; border-left:3mm solid var(--kuning); padding-left:4mm; }}
p, li {{ font-size:15.5pt; line-height:1.38; margin:0 0 3mm; }}
ul {{ margin:0; padding-left:8mm; }}
.full {{ grid-column: 1 / span 2; }}
.alur {{ display:flex; align-items:center; gap:3mm; flex-wrap:nowrap; margin:3mm 0 5mm; }}
.kotak {{ background:#fff; border:0.8mm solid var(--biru2); border-radius:3mm; padding:3.5mm 4mm; font-size:14pt; font-weight:600; text-align:center; flex:1; }}
.kotak small {{ display:block; font-weight:400; color:var(--abu); font-size:11.5pt; }}
.panah {{ font-size:20pt; color:var(--biru2); }}
.angka {{ display:grid; grid-template-columns: repeat(4, 1fr); gap:5mm; margin-bottom:5mm; }}
.angka div {{ background:#fff; border-radius:3mm; padding:4mm; text-align:center; border-top:2mm solid var(--kuning); }}
.angka b {{ display:block; font-size:28pt; color:var(--biru); }}
.angka span {{ font-size:12.5pt; color:var(--abu); }}
img.g {{ width:100%; display:block; margin:2mm 0 1mm; }}
.ket {{ font-size:12pt; color:var(--abu); text-align:center; margin:0 0 3mm; }}
.dua {{ display:grid; grid-template-columns: 1.35fr 1fr; gap:5mm; align-items:start; }}
footer {{ position:absolute; left:0; right:0; bottom:0; background:var(--biru); color:#fff; padding:6mm 18mm; font-size:13pt; display:flex; justify-content:space-between; }}
</style></head><body>
<header><img src="logo_utm.jpeg" alt="Logo Universitas Trunojoyo Madura">
<div><p class="judul">Evaluasi Large Language Model Qwen2.5 untuk Ekstraksi Intent Perintah Kalimat Bebas Bahasa Indonesia pada Robot</p>
<p class="penulis">As'ad Bahauddin Ahmad &nbsp;·&nbsp; Vivi Tri Widyaningrum</p>
<p class="afil">Program Studi Teknik Mekatronika, Universitas Trunojoyo Madura · Asistensi Hibah Penelitian (MBKM Riset) LPPM UTM 2026</p></div></header>
<main>
<section><h2>Latar Belakang</h2>
<p>Robot laboratorium idealnya dapat diperintah dengan bahasa sehari-hari. Antarmuka suara konvensional hanya mengenali perintah berstruktur tetap. LLM praterlatih menjanjikan pemahaman kalimat bebas, tetapi evaluasinya untuk Bahasa Indonesia secara <i>offline</i> masih jarang.</p>
<h2 style="margin-top:5mm">Tujuan</h2>
<ul><li>Mengukur akurasi Qwen2.5 1.5B mengekstrak <i>intent</i> dan entitas dari perintah kalimat bebas.</li>
<li>Mengukur <i>latency</i> dari suara hingga JSON perintah robot.</li>
<li>Membandingkan dengan <i>rule-based</i> dan IndoBERT pada tiga tingkat formalitas.</li></ul></section>
<section><h2>Dataset dan Evaluasi</h2>
<ul><li><b>162 ujaran kalimat bebas</b> dari 3 responden (bahasa ibu Madura dan Jawa), berdasarkan kartu skenario.</li>
<li><b>6 intent</b>: navigate_room, navigate_object, find_person, deliver_document, combined_command, general_command (27 ujaran per intent).</li>
<li><b>3 formalitas</b>: formal, semi-formal, informal (54 ujaran masing-masing).</li>
<li>Masukan: teks acuan dan transkrip Whisper; platform laptop GPU dan CPU; uji McNemar untuk perbedaan antarmetode.</li></ul></section>
<section class="full"><h2>Metode: Pipeline Offline Suara → JSON</h2>
<div class="alur"><div class="kotak">Mikrofon<small>48 kHz → 16 kHz</small></div><div class="panah">➜</div>
<div class="kotak">Silero VAD<small>pre-roll 300 ms, jeda 1,2 s</small></div><div class="panah">➜</div>
<div class="kotak">Whisper base<small>faster-whisper + prompt domain</small></div><div class="panah">➜</div>
<div class="kotak">NLU<small>Qwen2.5 1.5B · Rule-based · IndoBERT</small></div><div class="panah">➜</div>
<div class="kotak">JSON perintah robot<small>intent + entitas + steps</small></div></div>
<p>Qwen2.5 1.5B (Q4_K_M) dijalankan melalui Ollama dengan <i>structured output</i> berbasis JSON Schema dan <i>temperature</i> 0. Rule-based memakai kamus kata kunci; IndoBERT di-<i>fine-tune</i> dengan 300 kalimat sintetis.</p></section>
<section class="full"><h2>Hasil</h2>
<div class="angka"><div><b>{f(lat('gpu','t_respons')['mean'],2)} s</b><span>waktu respons pipeline (laptop GPU)</span></div>
<div><b>{f(wer_vad)}%</b><span>WER Whisper base (segmen VAD)</span></div>
<div><b>{f(acc('gpu','teks','indobert'))}%</b><span>intent accuracy IndoBERT (teks)</span></div>
<div><b>{f(acc('gpu','teks','qwen'))}%</b><span>intent accuracy Qwen2.5 (teks)</span></div></div>
<div class="dua"><div><img class="g" src="{G}akurasi_id.png" alt="Grafik akurasi"><p class="ket">Intent Accuracy dan Exact Match tiga metode pada tiga jenis masukan (laptop GPU, n = 162)</p>
<img class="g" src="{G}formalitas_id.png" alt="Grafik formalitas"><p class="ket">Intent Accuracy per tingkat formalitas</p></div>
<div><img class="g" src="{G}cm_qwen_id.png" alt="Confusion matrix Qwen2.5"><p class="ket">Confusion matrix Qwen2.5 (teks): perintah majemuk hampir selalu dianggap perintah tunggal (recall {f(comb['r'],2)})</p>
<img class="g" src="{G}latency_id.png" alt="Grafik latency"><p class="ket">Waktu komputasi per tahap: laptop GPU vs CPU</p></div></div></section>
<section class="full"><h2>Kesimpulan</h2>
<ul><li><b>Akurasi:</b> Qwen2.5 mencapai {f(acc('gpu','teks','qwen'),2)}% (teks) dan {f(acc('gpu','vad','qwen'),2)}% (pipeline suara); target 80% belum tercapai. Kelemahan utama: perintah majemuk.</li>
<li><b>Perbandingan:</b> IndoBERT terbaik untuk <i>intent</i> ({f(acc('gpu','teks','indobert'),2)}% teks; {f(acc('gpu','vad','indobert'),2)}% pipeline); rule-based terbaik untuk <i>exact match</i> pada transkrip ({f(acc('gpu','vad','rule','exact_match'),2)}%). Qwen2.5 tidak lebih unggul pada kalimat informal.</li>
<li><b>Latency:</b> pipeline <i>offline</i> merespons {f(lat('gpu','t_respons')['mean'],2)} ± {f(lat('gpu','t_respons')['sd'],2)} s di laptop GPU dan {f(lat('cpu','t_respons')['mean'],2)} ± {f(lat('cpu','t_respons')['sd'],2)} s di CPU, di bawah target 15 s.</li>
<li><b>Saran:</b> pemecahan klausa sebelum LLM, model/ASR yang lebih besar, pengujian di Raspberry Pi 5, dan integrasi ke robot.</li></ul></section>
<section><h2>Ruang Lingkup &amp; Keterbatasan</h2>
<ul><li>Yang dievaluasi adalah modul pemahaman perintah (keluaran JSON perintah robot); penggerakan robot fisik di luar ruang lingkup.</li>
<li>Pengujian dilakukan pada laptop secara <i>offline</i> karena Raspberry Pi 5 tetap tidak dapat <i>booting</i> walaupun sudah dicoba berulang kali dan kartu microSD diganti.</li>
<li>Responden hanya 3 orang; penutur data pengembangan juga merupakan salah satu responden (R03).</li></ul></section>
<section><h2>Ucapan Terima Kasih</h2>
<p>Penelitian ini didukung Program Asistensi Hibah Penelitian (MBKM Riset) LPPM Universitas Trunojoyo Madura. Terima kasih kepada Laboratorium Sistem Otomasi, Program Studi Teknik Mekatronika, dan para responden yang bersedia direkam.</p></section>
</main>
<footer><span>Kode sumber: github.com/asadbahauddin/qwen25-indonesian-voice-command-intent</span><span>Kontak: 230491100034@student.trunojoyo.ac.id</span></footer>
</body></html>"""
html = html.replace("font-size:23pt*0;", "")
(OUT / "poster.html").write_text(html, encoding="utf-8")
uri = (OUT / "poster.html").as_uri()
subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                f"--print-to-pdf={OUT / 'poster.pdf'}", uri], check=True, capture_output=True, timeout=120)
subprocess.run([EDGE, "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files", "--window-size=2245,3179",
                f"--screenshot={OUT / 'poster_pratinjau.png'}", uri], check=True, capture_output=True, timeout=120)
print("poster.pdf", (OUT / "poster.pdf").stat().st_size, "| pratinjau", (OUT / "poster_pratinjau.png").stat().st_size)
