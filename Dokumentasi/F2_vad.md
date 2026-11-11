# F2 — Silero VAD real-time + pre-roll

**Tanggal:** 12 November 2026 · **Status:** selesai. Parameter final **threshold 0,5 / min_silence 1200 ms**, dipilih dengan aturan pra-ditetapkan pada data pengembangan (lihat "Hasil data pengembangan").

## File
| File | Isi |
|---|---|
| `src/vad.py` | `SileroVAD` (torch/onnx), `VADSegmenter` (state machine streaming + pre-roll), `segment_array` |
| `bench/tes_vad.py` | Uji pada 162 rekaman (waktu komputasi, sapuan parameter, dampak ke Whisper) dan mode `--mic` real-time (`recordings/vad/seg_*.wav`) |
| `config.yaml` → `vad` | threshold, histeresis, pre-roll, min_silence, post-pad, min_speech, max_utterance |
| `results/vad_MSI_20261112_014026.{md,json}` | Hasil |
| `bench/sesi_dev.py`, `bench/kartu_dev.json` | Sesi rekam gabungan data pengembangan (lihat bawah) |

Pustaka: silero-vad 6.2.3 (`load_silero_vad(onnx=...)`), onnxruntime 1.31.0. API dicek dengan `inspect`. Model hanya menerima frame tepat 512 sampel @ 16 kHz (32 ms).

## Cara kerja
1. Audio mic → 16 kHz (`src/audio_io.py`) → dipotong per 512 sampel → Silero memberi p(ucapan) per frame.
2. **Diam:** frame disimpan di ring buffer **pre-roll 300 ms**. Bila p ≥ 0,5, ujaran dimulai dan isi ring buffer ikut diambil, sehingga awal kata yang lemah (mis. konsonan "t", "s") tidak hilang.
3. **Ujaran:** dianggap diam bila p < 0,35 (histeresis 0,15, sama dengan bawaan Silero). Diam ≥ **min_silence** berarti ujaran selesai. Ekor diam dipangkas sampai 200 ms. Ujaran < 250 ms dibuang (klik/batuk). Ujaran > 15 s dipotong paksa.
4. Waktu komputasi model dicatat per ujaran (`t_vad`). Jeda akhir (`tunggu_akhir_s` ≈ min_silence) dicatat terpisah, karena **jeda inilah komponen latency VAD yang dirasakan pengguna**.

Sebelumnya `VADIterator` bawaan Silero dicek, tetapi tidak dipakai karena tidak punya pre-roll dan batas durasi.

## Hasil (laptop, 162 rekaman responden, n = 25.202 frame)
**Waktu komputasi (CPU, 1 thread):** torch 0,329 ± 0,594 ms/frame, onnx **0,237 ± 0,154 ms/frame** (RTF 0,007). Selisih probabilitas maksimum 1×10⁻⁵ (setara). Diputuskan **ONNX**: lebih cepat dan lebih stabil, dan lebih relevan untuk RPi 5. Diukur ulang di F7.

**Akurasi batas ujaran:** acuannya rentang energi frame > -45 dBFS. Deretan aktif < 128 ms diabaikan, karena itu klik tombol Enter push-to-talk; Silero sudah benar mengabaikannya (p < 0,2).
- Pada threshold 0,5 tidak ada awal maupun akhir ucapan yang terpotong, untuk semua nilai min_silence ≥ 500 ms.
- Segmen dimulai rata-rata 0,261 s (minimum 0,192 s) sebelum ucapan, dan berakhir rata-rata 0,515 s (minimum 0,224 s) sesudahnya.

**Ujaran terpecah (temuan utama):** responden berhenti sejenak di tengah perintah kalimat bebas. Jeda terpanjang per ujaran rata-rata 0,624 s, p90 1,053 s, maksimum 1,664 s.

| threshold 0,5, min_silence | 500 ms | 800 ms | 1000 ms | 1200 ms | 1500 ms |
|---|---|---|---|---|---|
| ujaran terpecah (> 1 segmen) | 66/162 | 28/162 | 17/162 | 7/162 | 1/162 |

Makin panjang min_silence, makin sedikit ujaran terpecah, tetapi pengguna menunggu lebih lama setelah selesai bicara (latency +min_silence).

**Dampak ke Whisper:** transkrip faster-whisper (GPU, prompt) dari segmen VAD (0,5/800, segmen disambung) identik dengan transkrip audio utuh hanya pada 69/162 file. WER antar keduanya 21,54%. Whisper base sensitif terhadap pemotongan diam. Mana yang lebih akurat baru bisa diketahui setelah transkrip manual tersedia (F3 tahap 2).

**Mode mic:** berjalan tanpa galat (uji 5 s, 0 ujaran karena tidak ada yang berbicara).

## Masalah dan ancaman validitas
1. **Data responden adalah set uji.** Sapuan di atas hanya **karakterisasi**. Kalau min_silence dipilih dari tabel itu, terjadi penyetelan pada set uji, yang dilarang oleh aturan pemisahan data. Nilai aktif tetap **0,5 / 800 ms**, yang ditetapkan sebelum melihat data. Usulan: pilih min_silence dari data pengembangan terpisah (lihat bawah).
2. Noise gate transmitter membuat kondisi diam "sempurna". Pemicu palsu oleh bising lab tidak bisa diuji dari data ini, jadi perlu uji mic langsung di lab.
3. Dataset direkam push-to-talk, sehingga diam di awal dan akhir rekaman pendek (diam akhir minimum 0,2 s). Pada min_silence ≥ 800 ms, ujaran berakhir karena file habis (`akhir`), bukan karena deteksi diam.

## Data pengembangan VAD (disetujui peneliti 12 Nov 2026)
Satu **sesi rekam gabungan** (`bench/sesi_dev.py`) supaya mic hanya dipasang sekali:
1. **Suasana 30 s** tanpa bicara, untuk menguji pemicu palsu.
2. **Pilot 36 kalimat dibaca** (P01). Klip per kalimat sekaligus mengisi `recordings/pilot_audio/` untuk WER pilot.
3. **18 kartu dev kalimat bebas** (`bench/kartu_dev.json`, 3 per intent, formalitas 6/6/6). Kartu ditulis sebagai *situasi*, berbeda dari 54 kartu dataset (dicek otomatis: 0 sama).

Audio direkam **terus-menerus**, dan Enter hanya menandai batas item. Aliran lengkap (`stream.wav`) dan penanda waktu (`sesi.json`) disimpan, sehingga parameter VAD dapat diuji ulang offline tanpa merekam lagi.

**Aturan pemilihan parameter, ditetapkan sebelum data dev direkam:** min_silence terkecil (lalu threshold paling dekat 0,5) yang memenuhi semua syarat berikut pada item pilot + dev:
- ujaran terpecah ≤ 5% item;
- 0 item terlewat;
- 0 awal/akhir terpotong;
- 0 pemicu palsu saat suasana.

Analisis dijalankan dengan `python bench/tes_vad.py --dev recordings/dev/<folder>`. Ada juga pemeriksaan konsistensi: jumlah ujaran VAD live harus sama dengan simulasi offline dengan konfigurasi yang sama.

Di F9, WER dan NLU dilaporkan untuk dua masukan audio: rekaman utuh dan segmen VAD.

## Hasil data pengembangan (sesi P01, 12 Nov 2026)
Sumber final: `results/vad_dev_MSI_20261112_041005.md` (54 item). Sebelumnya `..._040608.md` (53 item, sebelum P03 direkam ulang). Folder sesi `recordings/dev/P01_20261112_{035400,035458,035546,040351,040941}` (lokal).

- **Data:** ±6,7 menit audio kontinu. 36 kalimat pilot dan 18 kartu dev dianalisis (54 item), ditambah 3 rekaman suasana × 30 s.
- **Dikeluarkan sebelum sapuan** (aturan kualitas data yang tidak bergantung parameter):
  - P01 dan P02 dari percobaan pertama: klip 0,03 s karena Enter dari paste perintah. Sudah direkam ulang.
  - P03 percobaan kedua: rekaman hening (puncak −60 dBFS). Sudah direkam ulang (sesi 040941).
- **Koreksi alat ukur** (setelah sapuan pertama, sebelum memilih parameter): kriteria "awal terpotong" semula menghitung **ekor ucapan item sebelumnya** yang melewati Enter sebagai awal ucapan item berikutnya. Contohnya D12 dan D14: ucapan sebenarnya baru mulai 3,5–4 s kemudian dan tertangkap utuh. Ini terlihat dari nilai yang sama (2) pada **semua** kombinasi parameter. Definisi dikoreksi: audio yang sudah tercakup segmen item sebelumnya tidak dihitung. Angka mentah tetap dilaporkan di kolom "(mentah)". Sapuan pertama tanpa koreksi: `results/vad_dev_MSI_20261112_040500.md` (tidak ada kombinasi yang lolos).

| threshold 0,5, min_silence | 500 | 800 | 1000 | **1200** | 1500 |
|---|---|---|---|---|---|
| terpecah (dari 54 item) | 8 | 6 | 4 | **2 (3,7%)** | 1 |
| terlewat / tergabung | 0 | 0 | 0 | **0** | 3 |
| pemicu palsu (3 × 30 s suasana) | 0 | 0 | 0 | **0** | 0 |
| awal / akhir terpotong | 0/0 | 0/0 | 0/0 | **0/0** | 0/0 |

**Terpilih menurut aturan: threshold 0,5, min_silence 1200 ms** (disetujui peneliti 12 Nov 2026). Pada 1500 ms, dua perintah berurutan bergabung menjadi satu segmen (3 item "terlewat"). Konsekuensinya, jeda tunggu setelah selesai bicara naik dari 0,8 menjadi 1,2 s (masuk ke `t_respons`).

Hasil ini konsisten dengan karakterisasi set uji yang dibuat sebelumnya: pada 1200 ms, 7/162 terpecah (4,3%). Set uji tidak dipakai untuk memilih.

- **Konsistensi live vs offline:** pada config yang sama, live 55 dan offline 56 ujaran. Selisih 1 karena simulasi offline memanggil `flush()` di akhir aliran, sedangkan live tidak.
- **Pemicu palsu = 0** pada 90 s suasana lab. Catatan: noise gate transmitter ikut membantu.

## Cara menjalankan
```powershell
$PY = "C:\Users\indie\.conda\envs\mbkm-nlu\python.exe"
& $PY bench\tes_vad.py                 # uji dataset (+ASR)
& $PY bench\tes_vad.py --mic --detik 60
```

## Kalimat logbook
> Mengimplementasikan segmentasi ujaran real-time dengan Silero VAD (ONNX, 0,24 ms per frame 32 ms) dan pre-roll 300 ms tanpa ada awal ucapan yang terpotong; ditemukan bahwa jeda di tengah perintah kalimat bebas (hingga 1,66 s) memecah 28 dari 162 ujaran pada min_silence 800 ms.
