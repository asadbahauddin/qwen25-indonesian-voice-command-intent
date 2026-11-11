# F9 — Evaluasi penuh (alat + uji coba pada pilot)

**Tanggal:** 12 November 2026 · **Status:** alat selesai dan diuji penuh pada **audio pilot** (set pengembangan). Evaluasi set uji (162 rekaman responden) menunggu koreksi transkrip dan label final.

## File
| File | Isi |
|---|---|
| `bench/evaluasi.py` | 3 metode × 3 masukan (teks / utuh / vad) × platform (laptop GPU / laptop CPU) |
| `results/eval_pilot_MSI_20261112_042305.{md,json}` | Hasil uji coba pada pilot (agregat + confusion matrix) |
| `recordings/pilot_audio/eval_item_pilot_*.csv` | Per item (lokal) |

## Cara menjalankan
```powershell
$PY = "C:\Users\indie\.conda\envs\mbkm-nlu\python.exe"
& $PY bench\evaluasi.py --data pilot                      # set pengembangan (uji coba)
& $PY bench\evaluasi.py --data dataset                    # set uji: hanya item terkoreksi + berlabel final
```
Sebelum evaluasi set uji:
- tutup aplikasi lain (RAM);
- colok listrik;
- pastikan `ollama serve` berjalan, **bukan** aplikasi Ollama. Ada pembaruan v0.40.16 yang menunggu terpasang, sedangkan versi penelitian 0.30.6.

## Desain
- **Masukan:**
  - `teks` = transkrip ground-truth (galat NLU saja);
  - `utuh` = rekaman utuh → Whisper → NLU;
  - `vad` = VAD (simulasi streaming, segmen disambung) → Whisper → NLU = pipeline lengkap.
- **Metrik:** definisinya sama dengan F3 (`wer_of`) dan F6 (`exact_match`, `metrics`), karena fungsi yang sama di-import.
- **Pemanasan:** 3 item pertama dijalankan dulu per platform dan tidak dihitung. Temuan F5: panggilan pertama di CPU 2–3× lebih lambat.
- **Waktu respons** = `min_silence` (1,2 s) + Whisper + NLU. Rekaman file bisa habis sebelum jeda tercapai, sehingga yang dipakai adalah jeda yang dialami pengguna saat pemakaian langsung.
- **Pengaman Ollama:** versi Ollama dan digest model dicek lalu dicatat. Kalau Ollama tidak terjangkau, evaluasi **berhenti** alih-alih mencatat akurasi 0%. Temuan: uji coba pertama memberi Qwen 0% karena server Ollama mati.
- Laporan hanya menghitung angka untuk H1–H3; interpretasinya dilakukan peneliti.

## Hasil uji coba pada pilot (n = 36, P01, set pengembangan)
Sumber: `results/eval_pilot_MSI_20261112_042305.md`. **Ini bukan uji hipotesis.** Pilot dipakai untuk mengembangkan prompt, sedangkan kamus rule-based dan data latih IndoBERT disusun dengan kosakata yang sama (ancaman validitas F6).

| Platform | VAD (s) | Whisper (s) | Qwen2.5 (s) | Total (s) | Waktu respons (s) |
|---|---|---|---|---|---|
| Laptop GPU (RTX 2050) | 0,0883 ± 0,0619 | 0,200 ± 0,050 | 1,096 ± 0,378 | 1,384 ± 0,433 | 2,496 ± 0,407 |
| Laptop CPU (i5-12450H) | 0,0691 ± 0,1321 | 1,077 ± 0,473 | 2,603 ± 1,052 | 3,749 ± 1,266 | 4,880 ± 1,205 |

Akurasi pada laptop GPU (Intent Accuracy / Exact Match, %):

| Metode | teks | utuh | vad |
|---|---|---|---|
| Qwen2.5 1.5B | 80,56 / 69,44 | 75,00 / 44,44 | 80,56 / 44,44 |
| Rule-based | 100 / 100 | 69,44 / 61,11 | 69,44 / 63,89 |
| IndoBERT | 100 / 100 | 86,11 / 58,33 | 91,67 / 55,56 |

WER (GPU, n=36): audio utuh 38,75%, segmen VAD 35,00%.

## Pengamatan
1. **Reproduksibilitas:** hasil Qwen pada teks di GPU (80,56 / 69,44) **sama persis** dengan F6 skema v2 (`results/summary_MSI_20261111_230143.md`).
2. **Qwen GPU vs CPU tidak identik.** Pada teks, EM GPU 69,44% dan CPU 72,22%; angka per formalitas juga berbeda. Penyebabnya perbedaan numerik kernel GPU/CPU, walaupun temperature 0 dan seed sama. Konsekuensinya, akurasi dilaporkan **per platform**.
3. **Galat ASR merambat ke NLU.** Dari teks ke transkrip, EM semua metode turun sekitar 25–45 poin. Akurasi intent rule-based paling terpukul (100 → 69%), sedangkan intent Qwen pada masukan vad tetap 80,6%.
4. **Segmen VAD sedikit menurunkan WER** dibanding audio utuh (35,00 vs 38,75%), karena diam dan bunyi klik di awal klip dibuang.
5. **RAM tersedia minimum 0,39 GB** selama uji. Swap mungkin terjadi, dan SD latency CPU besar.

## Kalimat logbook
> Membangun alat evaluasi penuh (3 metode × teks/transkrip × laptop GPU/CPU) dan mengujinya pada audio pilot: waktu respons pipeline Qwen 2,50 ± 0,41 s di GPU dan 4,88 ± 1,21 s di CPU, serta galat Whisper (WER 35–39%) menurunkan Exact Match semua metode.
