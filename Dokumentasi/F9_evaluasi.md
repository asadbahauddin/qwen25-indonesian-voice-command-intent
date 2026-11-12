# F9 — Evaluasi penuh (alat + uji coba pada pilot)

**Tanggal:** 12 November 2026 · **Status:** **selesai.** Evaluasi set uji 162 ujaran (`results/eval_dataset_MSI_20261112_095743.md`) dan analisis lanjutan (`results/analisis_dataset_MSI_20261112_104423.md`).

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

## Hasil set uji (162 ujaran, 3 responden, 12 Nov 2026)
Sumber: `results/eval_dataset_MSI_20261112_095743.md` dan `results/analisis_dataset_MSI_20261112_104423.md`. Perintah: `python bench/evaluasi.py --data dataset --perangkat gpu cpu --sensitivitas results/kebocoran_MSI_20261112_095154.json`, lalu `python bench/analisis_f9.py dataset/eval_item_dataset_MSI_20261112_095743.csv`. RAM tersedia minimum 0,16 GB selama uji.

**Latency pipeline lengkap (VAD → Whisper → Qwen2.5), n = 162 per platform**

| Platform | VAD (s) | Whisper (s) | Qwen2.5 (s) | Total (s) | Waktu respons (s) |
|---|---|---|---|---|---|
| Laptop GPU (RTX 2050) | 0,0761 ± 0,0876 | 0,200 ± 0,114 | 1,024 ± 0,433 | 1,300 ± 0,604 | 2,424 ± 0,528 (maks 4,34) |
| Laptop CPU (i5-12450H) | 0,0690 ± 0,0563 | 1,346 ± 1,231 | 2,822 ± 1,825 | 4,237 ± 2,826 | 5,368 ± 2,791 (maks 26,04) |

**WER Whisper base** (GPU): rekaman utuh 31,44%, segmen VAD 30,78%.

**Akurasi laptop GPU** (Intent Accuracy / Exact Match, %; F1 weighted = macro karena kelas seimbang)

| Metode | teks | utuh | vad (pipeline) |
|---|---|---|---|
| Qwen2.5 1.5B | 75,31 / 65,43 | 61,11 / 45,06 | 62,96 / 45,68 |
| Rule-based | 85,80 / 85,19 | 66,05 / 61,11 | 65,43 / 61,11 |
| IndoBERT | 96,30 / 85,19 | 84,57 / 54,94 | 83,95 / 56,17 |

**Hipotesis (angka; interpretasi peneliti):**
- **H1** (Qwen > 80% pada formal + semi-formal): GPU vad 62,04%, teks 78,70%; CPU vad 62,96%, teks 79,63% (n = 108) → **tidak tercapai**.
- **H2** (Qwen lebih robust pada informal): intent informal (GPU, vad) Qwen 64,8%, rule-based 63,0%, IndoBERT 79,6%. Pada teks: 68,5 / 90,7 / 98,1 → **tidak terdukung**. Qwen tidak lebih baik dari IndoBERT; dari rule-based tidak berbeda bermakna (intent, McNemar p = 0,71 pada vad GPU).
- **H3** (waktu respons < 15 s): GPU semua ujaran < 15 s (maks 4,34 s) → **tercapai**. CPU rata-rata 5,37 s, tetapi 4/162 ujaran > 15 s (maks 26,0 s, RAM tersedia 0,24–0,44 GB, kemungkinan swap).

**Temuan analisis:**
1. **Kelemahan utama Qwen ada pada `combined_command`** (recall 0,04 pada teks: hanya 1 dari 27 dikenali, sisanya dianggap perintah tunggal) dan `general_command` → `navigate_room` (13 item). Dari 40 kesalahan intent Qwen pada teks, sebagian besar berasal dari dua pola ini.
2. **McNemar:** IndoBERT lebih baik dari Qwen secara bermakna pada intent di semua masukan (p < 0,001). Untuk EM pada transkrip, rule-based > IndoBERT > Qwen; selisih Qwen–IndoBERT bermakna di GPU (p = 0,019 vad), tetapi tidak di CPU (p = 0,24).
3. **Galat ASR:** dari item yang EM-nya benar pada teks, sebanyak 37 (Qwen), 41 (rule-based), dan 49 (IndoBERT) menjadi salah pada transkrip. Galat entity (nama orang/ruangan salah dengar) dominan pada IndoBERT dan Qwen.
4. **Qwen GPU ≠ CPU:** JSON berbeda pada 13/162 item (teks) dan 43/162 (vad). Pada teks, CPU lebih baik secara bermakna (EM 70,99 vs 65,43%, p = 0,004). Hasil dilaporkan per platform.
5. **Uji sensitivitas** tanpa R03_S16/S46: perubahan ≤ 0,7 poin, sehingga kesimpulan tidak berubah.
6. Kontras dengan pilot: pada pilot (kosakata sama dengan kamus/data latih) rule-based dan IndoBERT 100%. Pada kalimat bebas responden, akurasi turun menjadi 85,8 dan 96,3% (teks).

## Kalimat logbook
> Mengevaluasi pipeline pada 162 ujaran kalimat bebas dari 3 responden: waktu respons Qwen2.5 2,42 ± 0,53 s (laptop GPU), tetapi akurasi intent Qwen (75,3% teks; 63,0% transkrip) lebih rendah dari IndoBERT (96,3%; 84,0%) dengan kelemahan utama pada perintah majemuk.
