# F3 — ASR Whisper base: openai-whisper vs faster-whisper

**Tanggal:** 12 November 2026 · **Status:** tahap 1 selesai (latency + draf transkrip). Tahap 2 (WER + pilihan final) menunggu koreksi transkrip manual.

## File
| File | Isi |
|---|---|
| `src/asr.py` | Kelas `ASR`: dua backend, antarmuka `transcribe(x16) -> (teks, info)` |
| `prompts/whisper_initial_id.txt` | initial_prompt domain (sha `555a3d3569c8`): hanya daftar nama entity lab, **bukan** kalimat dataset |
| `config.yaml` → `asr` | backend, model, bahasa, beam, compute type, prompt |
| `bench/tes_asr.py` | Benchmark 162 rekaman × 6 konfigurasi; WER otomatis bila referensi tersedia |
| `bench/koreksi_transkrip.py` | Alat koreksi transkrip manual (putar audio + 2 draf) |
| `results/asr_MSI_20261112_010730.{md,json}` | Ringkasan latency (agregat) |
| `dataset/asr_hipotesis_MSI_20261112_010730.csv` | Transkrip per file (lokal, tidak di-push) |

## Pustaka (versi terpasang, API dicek dengan `inspect.signature`)
faster-whisper 1.2.1 (CTranslate2 4.8.2, CUDA), openai-whisper 20250625 (torch 2.14.1+cu126), jiwer 4.0.0.
Tidak ada API deprecated yang dipakai.

## Keputusan teknis
- **Deterministik:** temperature 0 tanpa fallback, beam 5. Hasilnya bisa diulang dan dipertanggungjawabkan.
- **`condition_on_previous_text = false`:** mencegah halusinasi berantai. Ujaran kita pendek (satu segmen), jadi tidak ada konteks yang hilang.
- **`vad_filter = false`:** VAD adalah tahap tersendiri di pipeline (F2, Silero). Dalam benchmark ini rekaman push-to-talk dipakai utuh.
- **initial_prompt domain** berisi nama ruangan, benda, orang, dan dokumen dari `config/domain_id.yaml`. Ini pengetahuan domain yang memang dimiliki sistem, sama seperti kamus rule-based, sehingga tidak termasuk kebocoran data uji.
- **Compute:** faster-whisper float16 di GPU, int8 di CPU (setelan yang akan dipakai di RPi 5). openai-whisper fp16 di GPU, fp32 di CPU.
- **Konfigurasi CPU** di laptop hanya sebagai gambaran awal. Angka RPi 5 diukur di F7.

## Hasil tahap 1: latency (laptop MSI, RTX 2050, n = 162 file, durasi audio 4,98 s rata-rata)
Sumber: `results/asr_MSI_20261112_010730.md`

| Konfigurasi | Compute | Load (s) | t_asr (s) rata-rata ± SD | RTF |
|---|---|---|---|---|
| faster, GPU, prompt | float16 | 2,04 | 0,093 ± 0,019 | 0,019 |
| faster, GPU, tanpa prompt | float16 | 0,71 | 0,085 ± 0,016 | 0,018 |
| openai, GPU, prompt | float16 | 1,82 | 0,282 ± 0,085 | 0,057 |
| openai, GPU, tanpa prompt | float16 | 0,93 | 0,271 ± 0,090 | 0,055 |
| faster, CPU, prompt | int8 | 1,04 | 2,791 ± 1,106 | 0,578 |
| openai, CPU, prompt | float32 | 3,08 | 6,073 ± 3,125 | 1,286 |

- faster-whisper sekitar **3× lebih cepat di GPU** dan **2,2× lebih cepat di CPU** dibanding openai-whisper.
- initial_prompt menambah waktu kurang dari 0,01 s (GPU).
- Di CPU laptop, openai-whisper lebih lambat dari waktu nyata (RTF > 1).

## Pengamatan kualitatif (belum angka WER)
- Whisper **base** cukup sering salah pada kata umum Bahasa Indonesia ("tolong carikan" → "jarikan", "robot" → "Sabat/Protort").
- initial_prompt terlihat **memperbaiki nama entity**. Contoh R01_S30: tanpa prompt "serat Indonesia ini ke Pak Umang", dengan prompt "surat izin ini ke Pak Umam".
- initial_prompt juga bisa memicu **halusinasi pengulangan**: R03_S45 menjadi "trainer, trainer, trainer, …". Tiap konfigurasi mengalami 0–1 kasus dari 162.
- Hasil faster-whisper GPU float16 dan CPU int8 identik pada 104/162 file. Kuantisasi int8 sedikit mengubah keluaran.

## WER pada pilot (set pengembangan, P01 membaca 36 kalimat, 12 Nov 2026)
Sumber: `results/asr_pilot_MSI_20261112_040643.md`. Klip berasal dari sesi kontinu, termasuk jeda sebelum bicara.

| Konfigurasi | WER (n=36) | t_asr (s) |
|---|---|---|
| faster GPU + prompt | **38,75%** | 0,106 ± 0,021 |
| faster GPU tanpa prompt | 56,25% | 0,089 ± 0,018 |
| openai GPU + prompt | 39,58% | 0,298 ± 0,075 |
| openai GPU tanpa prompt | 57,50% | 0,269 ± 0,082 |
| faster CPU int8 + prompt | 39,58% | 0,930 ± 0,093 |

- n=36 masih **mengikutkan P03 yang hening** (WER 100%). Tanpa P03 (n=35), faster GPU + prompt = 37,45%. Angka final dihitung ulang setelah P03 direkam ulang.
- **initial_prompt menurunkan WER sekitar 17–18 poin**, dan berlaku untuk kedua backend.
- Akurasi faster-whisper dan openai-whisper **setara** (selisih < 1 poin), sedangkan faster-whisper ±3× lebih cepat. Usulan: **backend final = faster-whisper**, dipilih dari data pengembangan, sehingga set uji tidak dipakai untuk memilih.
- Galat Whisper base cukup berat pada kata umum: "Silakan temukan Ibu Vivi" → "Silatan nomukan Kus Vivi"; "Coba jalannya pelan-pelan" → "Jauhkan kembali". Sebagian kecil berupa beda pemenggalan ("keruang" vs "ke ruang"), yang tetap dihitung salah oleh WER.

## Tahap 2 (setelah koreksi transkrip)
1. Peneliti mengoreksi transkrip: `python bench/koreksi_transkrip.py`.
2. `python bench/tes_asr.py --hanya-wer dataset/asr_hipotesis_MSI_20261112_010730.csv` menghitung WER per konfigurasi, per responden, dan per formalitas.
3. Backend final dipilih dari WER dan latency (keputusan dicatat di CLAUDE.md).

**Konvensi transkrip ground-truth:**
- Tulis semua kata yang diucapkan, termasuk partikel dan kata gaul/daerah apa adanya.
- Bunyi ragu murni (eh, em, hmm) tidak ditulis.
- Nama ditulis sesuai kamus.
- Angka ditulis dengan huruf.
- Normalisasi WER: huruf kecil, tanda baca dihapus (tanda hubung menjadi spasi).

**Ancaman validitas:** draf Whisper bisa membuat penilai cenderung menerima teks draf (*anchoring*), sehingga WER tampak lebih rendah. Mitigasinya:
- Ditampilkan dua draf dari konfigurasi yang berbeda (faster+prompt dan openai tanpa prompt), agar penilai tidak berpihak pada satu sistem.
- Audio wajib diputar sebelum menjawab.
- Sumber tiap transkrip (draf1/draf2/ketik) dicatat untuk dilaporkan.

## Kalimat logbook
> Mengimplementasikan modul ASR Whisper base dengan dua backend (faster-whisper dan openai-whisper) dan mengukur latency transkripsi 162 rekaman responden: faster-whisper GPU 0,093 ± 0,019 s per ujaran, sekitar 3× lebih cepat dari openai-whisper.
