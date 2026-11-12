# CLAUDE.md — Konteks Proyek Riset MBKM (dibaca otomatis oleh Claude Code)

> File ini adalah "memori" proyek. Claude Code wajib membacanya di awal setiap sesi
> dan **memperbarui bagian `## Status Proyek` di akhir setiap fase**, supaya konteks
> tidak hilang walaupun riwayat chat terhapus.

## 1. Identitas riset
- **Judul:** Evaluasi Large Language Model Qwen2.5 untuk Ekstraksi Intent Perintah Kalimat Bebas Bahasa Indonesia pada Robot
- **Program:** Asistensi Hibah Penelitian (MBKM Riset), LPPM Universitas Trunodjoyo Madura
- **Mahasiswa:** As'ad Bahauddin Ahmad (Teknik Mekatronika)
- **Pembimbing:** Ir. Vivi Tri Widyaningrum, S.Kom., M.T.
- **Lokasi:** Laboratorium Sistem Otomasi, Teknik Mekatronika UTM

### Tenggat LPPM
| Tanggal | Kegiatan |
|---|---|
| s.d. 27 Nov 2026 | Akhir tahap pelaksanaan (semua pengujian harus selesai) |
| 2 Nov – 5 Des 2026 | Penyusunan luaran (artikel, HKI, poster, video) |
| 30 Nov – 8 Des 2026 | Laporan akhir |
| 9 – 10 Des 2026 | Seminar hasil |

## 2. Desain penelitian (sudah disetujui di proposal — jangan diubah tanpa izin saya)
**Pipeline:** Mikrofon → Silero VAD → Whisper base → NLU → JSON perintah robot

**Tiga metode NLU yang dibandingkan** (antarmuka sama: `predict(text) -> (json, info)`):
1. **Qwen2.5 1.5B Q4_K_M** via Ollama (`qwen2.5:1.5b`), prompt engineering, keluaran JSON terstruktur — metode utama.
2. **Rule-based keyword matching** — baseline bawah.
3. **IndoBERT fine-tuned** (`indobenchmark/indobert-base-p1`, ±300 kalimat latih, 50/intent) — baseline supervised (BUKAN "upper bound").

**Enam intent:** `navigate_room`, `navigate_object`, `find_person`, `deliver_document`, `combined_command`, `general_command`

**Skema JSON** (finalkan dengan saya bila belum final):
```json
{"intent": "<salah satu dari 6>", "room": "string|null", "object": "string|null",
 "person": "string|null", "document": "string|null", "steps": "array|null"}
```

**Metrik:**
- ASR: **WER** (pakai `jiwer`, normalisasi huruf kecil + tanda baca).
- NLU: **Intent Accuracy**, **Exact Match** (intent + seluruh entity harus tepat), **F1 weighted & macro**, **confusion matrix**, % JSON valid.
- **Latency per tahap** (VAD, ASR, NLU, total) — rata-rata ± SD dengan n jelas.
- Ketiga metode NLU diuji pada **dua masukan**: teks ground-truth dan transkrip Whisper (untuk memisahkan galat ASR dari galat NLU).
- Variasi **formalitas**: formal, semi-formal, informal.

**Hipotesis (dari proposal):** H1 akurasi Qwen > 80% untuk formal & semi-formal di RPi 5 (80% = target yang ditetapkan peneliti). H2 Qwen lebih robust dari IndoBERT & rule-based pada kalimat informal. H3 latency end-to-end < 15 s di RPi 5.

**Pemisahan data (wajib, cegah data leakage):**
- `bench/pilot_set.json` — set pilot sintetis, hanya untuk uji pendahuluan.
- `data/indobert_train.jsonl` — data latih IndoBERT.
- `dataset/` — dataset penelitian (audio responden). **Tidak boleh ada kalimat yang sama di ketiganya.**

**Dataset penelitian:** 3–5 responden, 150–250 sampel audio, WAV 16 kHz mono 16-bit, berlabel transkrip + intent + entity + formalitas + id responden. Dataset ini adalah **luaran HKI (hak cipta dataset)** → wajib ada metadata, lembar persetujuan responden, dan data card.

## 3. Perangkat
- **Laptop:** GPU NVIDIA RTX 2050 (VRAM 4 GB) — pengembangan.
- **Target:** ~~Raspberry Pi 5 8GB~~ → **diganti laptop** (keputusan peneliti 12 Nov 2026: waktu mepet, microSD RPi rusak). Semua pengujian fully offline di laptop. RPi 5 = saran penelitian lanjutan/skripsi.
- **Mikrofon:** wireless lavalier, receiver USB (biasanya 44,1/48 kHz → wajib resample ke 16 kHz).

## 4. Lingkungan & alat
- **conda** (BUKAN venv). Env: `mbkm-nlu`, Python 3.11, didefinisikan di `environment.yml`. Paket non-conda dipasang dengan `pip` di dalam env dan dicatat di bagian `pip:`.
- RPi 5: Miniforge aarch64, PyTorch CPU.
- **Setiap selesai fase (wajib):**
  1. `conda env export --no-builds > environment.yml`
  2. `git add -A && git commit -m "<fase>: <ringkas>" && git push`
- **Setiap sesi wajib di-push ke GitHub** (permintaan peneliti, 11 Nov 2026).
- Pustaka utama: `sounddevice`, `soxr`/`scipy`, `silero-vad`, `faster-whisper` dan/atau `openai-whisper` (pilih berdasarkan pengukuran), `ollama`/HTTP API, `transformers`, `jiwer`, `scikit-learn`, `rich`.

## 5. Struktur repo
```
CLAUDE.md  environment.yml  config.yaml  README.md
prompts/system_id.txt          # system prompt Qwen, berversi
config/keywords_id.yaml        # kamus rule-based
src/audio_io.py  src/vad.py  src/asr.py
src/nlu/base.py  src/nlu/qwen.py  src/nlu/rule.py  src/nlu/indobert.py
src/pipeline.py  src/cli.py    # CLI interaktif: ganti metode tanpa restart
bench/  data/  dataset/  models/  recordings/  results/  logs/
```

## 6. Aturan kerja Claude Code
1. **Per fase**, berhenti di akhir fase, tunjukkan bukti (perintah + output asli), tunggu saya bilang "lanjut".
2. **Jangan pernah mengarang angka.** Semua latency/akurasi dari eksekusi nyata dan tersimpan di `results/`.
3. Cek versi pustaka terpasang + dokumentasinya sebelum memakai API; beri tahu jika ada yang deprecated.
4. Jelaskan keputusan teknis singkat — saya harus bisa mempertanggungjawabkannya di seminar.
5. Jangan hapus/tulis ulang file saya tanpa bertanya. Perubahan besar → branch baru.
6. Konfigurasi di `config.yaml`, logging ke `logs/`, tanpa hard-code.
7. Di akhir tiap fase berikan: daftar file, cara menjalankan, angka nyata, masalah, **1 kalimat untuk logbook**, lalu perbarui `## Status Proyek`.

## 7. CLI interaktif (`src/cli.py`)
Model dimuat sekali; perintah tanpa restart Python:
`/metode qwen|rule|indobert|semua` · `/mode mic|teks` · `/whisper base|small` · `/beam <n>` · `/stat` · `/reset` · `/simpan` · `/bantuan` · `/keluar`.
Setiap perintah menampilkan (pakai `rich`): transkrip, JSON, tabel latency (t_vad, t_asr, t_nlu, t_total, + load/prompt_eval/eval & tokens/s untuk Qwen), metode aktif, `json_valid`; di RPi 5 juga suhu CPU.

## 8. Format tabel untuk laporan (kolom harus persis)
- **Tabel latency:** Platform | VAD (s) | Whisper (s) | Qwen2.5 (s) | Total (s) — rata-rata ± SD, sebutkan n.
- **Tabel akurasi:** Metode | Jumlah kalimat uji | Intent Accuracy | Exact Match (+ F1 weighted/macro untuk laporan akhir).
- Ringkasan otomatis ke `results/summary_<host>_<timestamp>.md`.

## 9. Fase pekerjaan
| Fase | Isi |
|---|---|
| F0 | Cek lingkungan, conda env, CUDA, Ollama |
| F1 | Tes mikrofon: daftar perangkat, rekam diam/normal/keras, RMS/peak/clipping/SNR |
| F2 | Silero VAD real-time + pre-roll, `bench/tes_vad.py` |
| F3 | Whisper base: openai-whisper vs faster-whisper, initial_prompt domain |
| F4 | Qwen2.5 via Ollama, JSON schema, `prompts/system_id.txt` |
| F4b | Baseline rule-based + IndoBERT (antarmuka sama) |
| F5 | Integrasi pipeline + CLI interaktif + log CSV |
| F6 | Uji pendahuluan teks (pilot 36 kalimat, 3 metode) → tabel laporan |
| F7 | Deployment & benchmark Raspberry Pi 5 (suhu, throttling) |
| F8 | Alat perekaman dataset responden (daftar kalimat, metadata, consent) |
| F9 | **Selesai** (12 Nov) | `bench/evaluasi.py`, `bench/analisis_f9.py`, `results/eval_dataset_MSI_20261112_095743.md`, `results/analisis_dataset_MSI_20261112_104423.md`, `Dokumentasi/F9_evaluasi.md` | Set uji 162: H1 tidak tercapai, H2 tidak terdukung (IndoBERT terbaik), H3 tercapai di GPU (CPU 4/162 > 15 s, swap). Kelemahan Qwen: combined_command (recall 0,04 teks). Sensitivitas tanpa 2 item mirip: ≤ 0,7 poin. |
| F10 | **Berjalan** (12 Nov) | `luaran/buat_laporan_akhir.js` → `Laporan_Akhir_MBKM_Asad_Bahauddin_Ahmad_DRAF.docx` (lokal), `Dokumentasi/Luaran_JoTI_ketentuan.md` | Draf laporan akhir lengkap (BAB I–V, angka nyata F9) dengan [ISI] untuk logbook minggu 8–12, foto, scan persetujuan, keputusan HKI. Belum: grafik (matplotlib belum terpasang), artikel JoTI, poster, paket dataset, berkas HKI. |

## Status Proyek
> Diperbarui oleh Claude Code di akhir setiap fase. Format: fase | status | bukti (file/commit) | catatan.
> **Audit terakhir: 11 Nov 2026 (sesi baru, riwayat chat lama hilang). Pembaruan terakhir: 12 Nov 2026 (F5 pipeline + CLI; RPi diganti laptop).**

| Fase | Status | Bukti | Catatan |
|---|---|---|---|
| F0 | **Selesai** (ulang 11 Nov) | `environment.yml`, `Dokumentasi/F0_lingkungan.md`, `Dokumentasi/F0_bukti_cek_env.{txt,png}` | Env conda `mbkm-nlu` (Py 3.11.18), torch 2.14.1+cu126 CUDA True, ctranslate2 4.8.2 CUDA, Ollama 0.30.6 + `qwen2.5:1.5b`. `.venv` lama (rusak) dihapus. |
| F1 | **Selesai** (11 Nov) | `bench/tes_mic.py`, `results/mic_MSI_20261111_222034.{md,json}`, `Dokumentasi/F1_tes_mic.md` | WASAPI 48 kHz → mono 16 kHz PCM_16 terverifikasi. Tidak ada clipping native. Transmitter punya **limiter + noise gate** (diam ±-91 dBFS), sehingga SNR akustik tidak terukur. Level ucapan normal p90 -13 dBFS (tinggi). |
| F2 | **Selesai** (12 Nov): threshold 0,5 / **min_silence 1200 ms** | `src/vad.py`, `bench/tes_vad.py`, `bench/sesi_dev.py`, `results/vad_MSI_20261112_014026.md`, `results/vad_dev_MSI_20261112_041005.md`, `Dokumentasi/F2_vad.md` | Silero ONNX 0,237 ± 0,154 ms/frame. Pre-roll 300 ms: 0 awal/akhir terpotong. Jeda di tengah perintah bebas memecah 28/162 ujaran (0,5/800 ms). Sapuan pada set uji = karakterisasi saja. Parameter dipilih aturan pra-ditetapkan pada data dev P01 (54 item): 1200 ms → 2 terpecah, 0 terlewat/terpotong/pemicu palsu. Kriteria "awal terpotong" dikoreksi (ekor item sebelumnya), angka mentah tetap dilaporkan. |
| F3 | **Backend final dipilih** (12 Nov): faster-whisper. WER dataset menunggu koreksi manual | `src/asr.py`, `bench/tes_asr.py`, `bench/koreksi_transkrip.py`, `prompts/whisper_initial_id.txt` (sha `555a3d3569c8`), `results/asr_MSI_20261112_010730.md`, `Dokumentasi/F3_whisper.md` | faster-whisper ≈3× lebih cepat dari openai-whisper. initial_prompt memperbaiki nama entity, tapi 1/162 halusinasi pengulangan. WER pilot (`results/asr_pilot_MSI_20261112_041011.md`, n=36): faster+prompt 38,75%, openai+prompt 39,58%, tanpa prompt 56–58%. Backend faster-whisper (setara akurasi, 3× lebih cepat). |
| F4 | **Selesai** (11 Nov) | `src/nlu/base.py`, `src/nlu/qwen.py`, `prompts/system_id.txt` v1 (sha `114d424e5d61`), `results/qwen_uji_cepat_MSI_*.txt`, `Dokumentasi/F4_qwen.md` | Ollama HTTP + structured output (JSON schema). Uji cepat 2 kalimat (sederhana + combined): JSON & skema valid, entity tepat. `load_s` 0,3–0,5 s per permintaan perlu diselidiki di F6. |
| F4b | **Selesai** (11 Nov) | `src/nlu/{rule,indobert,entities}.py`, `config/keywords_id.yaml` v1, `data/indobert_train.jsonl` (300), `results/indobert_train_MSI_20261111_225006.json`, `results/f4b_uji_cepat_*.txt`, `Dokumentasi/F4b_baseline.md` | Val acc IndoBERT 1,0 (val dari templat yang sama, jadi **bukan hasil uji**). Model di `models/indobert_intent` (tidak di-push, bisa dibuat ulang). Uji cepat 2 kalimat: kedua baseline benar. |
| F5 | **Selesai** (12 Nov) | `src/pipeline.py`, `src/cli.py`, `results/cli_MSI_20261112_033222.md`, `Dokumentasi/F5_pipeline.md` | CLI rich (metode/mode/whisper/beam/perangkat tanpa restart), log CSV `logs/pipeline_*.csv` (+ RAM tersedia). Uji asap saja (pilot + rekaman F1, bukan set uji). Diperbaiki: `num_gpu` Ollama harus eksplisit; silero-vad mengunci torch 1 thread saat import. RAM laptop 7,7 GB hampir penuh → lonjakan 20+ s, tutup aplikasi lain saat F9. |
| F6 | **Selesai** (11 Nov) | `bench/uji_llm.py`, `results/summary_MSI_20261111_225631.md` (+csv/json), `Dokumentasi/F6_uji_pilot.md` | Qwen intent 80,56% / EM 63,89%; rule & IndoBERT 100%. **Ancaman validitas:** pilot, templat, dan kamus disusun bersamaan dengan kosakata sama, jadi hasil F6 bukan uji hipotesis. Kesalahan Qwen dominan pada konsistensi struktur combined. |
| F7 | **Dibatalkan** (12 Nov, keputusan peneliti) | – | RPi 5 diganti laptop. Penyimpangan dari proposal (RM1, RM2, H1, H3 menyebut RPi 5) wajib dijelaskan di Kendala & Solusi laporan akhir. |
| F8 | **Selesai** (12 Nov): 162 transkrip + 162 label final, cek kebocoran | `bench/rekam_dataset.py`, `bench/cek_dataset.py`, `results/kualitas_dataset_MSI_20261112_005606.md`, `dataset/` (lokal, tidak di-push) | 3 responden × 54 = **162 WAV** lengkap, format 16 kHz mono PCM_16 semua benar, total 13,4 menit. Clipping ringan (limiter transmitter): R01 13/54, R02 1/54, R03 42/54 file, maks 0,051% sampel. Transkrip R01 terkoreksi 54/162 (11 kata depan tersambung dipisah sesuai EYD + S07 andu→andi, disetujui peneliti). Alat label (`bench/label_dataset.py`, draf = target kartu) dan cek kebocoran (`bench/cek_kebocoran.py`, R01: 0 sama/0 mirip, `results/kebocoran_MSI_20261112_044132.md`) siap. Lihat `Dokumentasi/F8_label.md`. |
| F9 | **Alat selesai, uji coba pilot** (12 Nov); set uji menunggu transkrip+label | `bench/evaluasi.py`, `results/eval_pilot_MSI_20261112_042305.md`, `Dokumentasi/F9_evaluasi.md` | 3 metode × teks/utuh/vad × GPU/CPU, pemanasan 3 item dibuang, cek versi Ollama + berhenti bila Ollama mati. Qwen GPU≠CPU (EM teks 69,44 vs 72,22) → akurasi dilaporkan per platform. |
| F10 | Belum | – | – |

**Keputusan teknis yang sudah diambil:**
- Audio ditangkap pada sample rate native perangkat, downmix mono, lalu di-resample streaming ke 16 kHz dengan `soxr.ResampleStream` kualitas HQ (`src/audio_io.py`, `config.yaml: audio`).
- Konfigurasi terpusat di `config.yaml`; log ke `logs/<nama>_<host>_<tanggal>.log` (`src/utils.py`).
- Lingkungan: conda `mbkm-nlu` + pip (versi ter-pin), PyTorch 2.14.1+cu126. CUDA toolkit sistem (11.2/11.8/12.1) dibiarkan; faster-whisper memakai `cublas64_12.dll` (v12.1) dan `cudnn64_9.dll` (v11.8), jadi **CUDA 11.8 jangan dihapus**. Cache pip laptop sengaja dinonaktifkan.
- Mic: receiver wireless lavalier `USBAudio1.0` (USB VID_4C4A PID_4155). Jangan pakai input "NVIDIA Broadcast" karena audionya diolah.
- F1: capture WASAPI 48 kHz (bukan dipaksa 16 kHz). Clipping diukur pada sinyal native, karena resampling soxr menimbulkan overshoot semu. Transmitter lavalier memakai limiter dan noise gate: SNR dari rekaman diam tidak boleh dilaporkan sebagai SNR akustik. Pre-roll VAD di F2 tidak bisa mengembalikan audio yang sudah dipotong gate.
- Kosakata domain lab (ruangan/benda/orang/dokumen) ada di `config/domain_id.yaml`. "Trainer RL" = trainer Rangkaian Listrik; ejaan "Pak Andi".
- **Skema JSON final** (disetujui 11 Nov): `combined_command` → field tingkat atas null, sub-perintah di `steps[]` (tiap langkah: intent selain combined + 4 entity). Skema didefinisikan di `src/nlu/base.py: COMMAND_SCHEMA`.
- F4: Qwen dipanggil lewat Ollama HTTP API (`requests`, tanpa paket `ollama`), `format`=JSON schema (grammar-constrained), temperature 0, seed 42, num_ctx 2048. Normalisasi entity (alias → kanonik) sama untuk semua metode. Contoh few-shot di prompt dihitung sebagai data latih Qwen, jadi tidak boleh muncul di pilot atau dataset.
- F4b: entity untuk rule-based dan IndoBERT memakai kamus bersama (`src/nlu/entities.py`, alias terpanjang, tanpa tumpang tindih). IndoBERT hanya mengklasifikasi intent; combined dipecah per klausa lalu diklasifikasi ulang. Data latih sintetis dari templat (seed 42), dicek tanpa kebocoran ke pilot dan contoh prompt. **Kamus rule-based tidak boleh disetel memakai pilot atau dataset.**
- **Skema v2** (disetujui 11 Nov) = skema resmi untuk validasi semua metode dan untuk `format` Qwen (`nlu.qwen.schema_version: v2`). Struktur dikunci per intent; v1 disimpan untuk pembanding.
- **Prompt final Qwen = v1** (`prompts/system_id.txt`, sha `114d424e5d61`) + skema v2. Prompt v2 (field `tindakan` dulu) sudah diuji: intent 86,11% tetapi EM 66,67% dan latency 1,024 s, jadi tidak dipakai. **Iterasi prompt dihentikan** agar tidak overfitting ke pilot.
- **Pilot = set pengembangan** (boleh dipakai memperbaiki prompt/skema). **Data responden = set uji** (tidak boleh dipakai untuk pengembangan apa pun).
- **Desain data responden (disetujui 11 Nov):** responden bicara langsung ke mic (alat rekam seperti `tes_mic`) dengan **kalimat bebas** berdasarkan **kartu skenario** (intent + entity target + gaya formalitas), bukan membaca kalimat. Transkrip dicek manual, lalu label disusun. Rekaman diuji untuk ketiga metode (teks ground-truth dan transkrip Whisper).
- **Responden: 3 orang (peneliti + 2 orang) × 54 kartu = 162 ujaran** (diputuskan 11 Nov). Peneliti sebagai responden adalah keterbatasan (mengenal sistem), jadi hasil juga dilaporkan per responden. Kalimat dataset wajib dicek tidak sama dengan pilot, data latih, dan contoh prompt.
- F3: Whisper deterministik (temperature 0 tanpa fallback, beam 5, condition_on_previous_text false, vad_filter false karena VAD tahap tersendiri). initial_prompt = daftar nama entity domain saja. Transkrip per file disimpan di `dataset/` (tidak di-push). Koreksi transkrip menampilkan 2 draf dari konfigurasi berbeda untuk mengurangi anchoring.
- F2: VAD = Silero ONNX + state machine sendiri (pre-roll 300 ms, histeresis 0,15, post-pad 200 ms, min_speech 250 ms). Parameter aktif 0,5/800 ms ditetapkan sebelum melihat data; **parameter VAD tidak boleh dipilih dari data responden** (set uji).
- **Platform (12 Nov, keputusan peneliti):** RPi 5 tidak dipakai; RM1/RM2/H1/H3 dijawab untuk platform laptop offline. Angka laptop **tidak boleh** diklaim sebagai kinerja RPi 5.
- **Luaran tambahan (12 Nov):** poster ilmiah + dataset penelitian (dengan data card/datasheet).
- **Skenario laptop CPU (disetujui 12 Nov):** latency dilaporkan untuk Laptop GPU dan Laptop CPU (Whisper int8 CPU, Qwen `num_gpu 0`, IndoBERT CPU) sebagai pendekatan perangkat tanpa GPU, tetap disebut "laptop CPU" (bukan RPi).
- **HKI (disetujui 12 Nov):** hak cipta **program komputer** (pipeline + CLI); dataset = luaran tambahan (hindari dihitung dua kali). Ikuti arahan Bu Vivi bila berbeda.
- F5: `nlu.qwen.num_gpu` eksplisit (99 GPU / 0 CPU) karena Ollama tetap di CPU bila opsi dihilangkan. `SileroVAD` mengembalikan `torch.get_num_threads()` setelah import silero (pustaka memanggil `set_num_threads(1)` global). Pemanasan realistis 2× per komponen; F9 buang ujaran awal sebagai pemanasan.
- **F2 final (12 Nov, disetujui):** min_silence 1200 ms, threshold 0,5 (aturan pra-ditetapkan, data dev P01, 54 item). Item tanpa ucapan dan take lama dikeluarkan sebelum sapuan.
- Data pilot audio (P01) = set pengembangan: boleh dipakai memilih backend Whisper.
- **F3 final (12 Nov, disetujui):** backend faster-whisper (`asr.backend: faster`), dipilih dari WER pilot (set pengembangan).
- Belum diputuskan: tidak ada untuk F2/F3. Prompt Qwen tetap v1 (iterasi dihentikan).
- **Ollama:** versi penelitian 0.30.6. Aplikasi Ollama sudah mengunduh v0.40.16 (belum terpasang) → jalankan `ollama serve`, jangan buka aplikasi sampai pengujian selesai.
- F9: waktu respons memakai jeda tunggu = min_silence (rekaman file bisa habis sebelum jeda tercapai).
- **F8 label (12 Nov):** label = yang diucapkan; draf = target kartu; 161/162 = target, R02_S29 document=null. Kamus domain TIDAK ditambah alias dari set uji (mis. "kusairi"). Kebocoran akhir: 0 sama, 2 mirip (R03_S16 prompt, R03_S46 latih IndoBERT, Jaccard 0,83) → **analisis utama 162 + uji sensitivitas tanpa 2 item** (keputusan peneliti).

**Angka yang sudah terukur:**
- F1 mic (`results/mic_MSI_20261111_222034.md`): diam RMS -90,94 dBFS; normal RMS -17,35 / p90 -13,21 dBFS; keras RMS -13,34 / p90 -7,87 dBFS; clipping native 0 untuk semua kondisi.
- F6 pilot teks, laptop (`results/summary_MSI_20261111_225631.md`): Qwen intent 80,56%, EM 63,89%, F1w 0,7931, JSON valid 100%, t_nlu 0,786 ± 0,387 s (n=36); rule-based 100%/100%, 0,0002 s; IndoBERT 100%/100%, 0,0174 ± 0,0240 s. Per formalitas Qwen (intent/EM): formal 83,3/75,0, semi 91,7/66,7, informal 66,7/50,0.
- F6 Qwen skema v2 (`results/summary_MSI_20261111_230143.md`): intent 80,56%, EM 69,44%, t_nlu 0,678 ± 0,239 s (n=36). Combined P25/P26/P29/P30 masih salah.
- F8 kualitas rekaman (`results/kualitas_dataset_MSI_20261112_005606.md`): durasi R01 4,50 ± 1,14 s, R02 5,89 ± 1,45 s, R03 4,55 ± 1,30 s (n=54 masing-masing); RMS rata-rata -16,6 / -21,9 / -15,4 dBFS.
- F3 latency Whisper base, laptop (`results/asr_MSI_20261112_010730.md`, n=162): faster GPU fp16 + prompt 0,093 ± 0,019 s (RTF 0,019); openai GPU fp16 + prompt 0,282 ± 0,085 s; faster CPU int8 2,791 ± 1,106 s; openai CPU fp32 6,073 ± 3,125 s.
- F2 VAD (`results/vad_MSI_20261112_014026.md`, n=162 file / 25.202 frame): onnx 0,237 ± 0,154 ms/frame, torch 0,329 ± 0,594; terpecah pada threshold 0,5: 800 ms 28/162, 1200 ms 7/162, 1500 ms 1/162; Whisper segmen VAD vs utuh identik 69/162 (WER antar keduanya 21,54%).
- F2 dev (`results/vad_dev_MSI_20261112_041005.md`, 54 item + 90 s suasana): th 0,5 terpecah 800 ms 6, 1000 ms 4, 1200 ms 2, 1500 ms 1 (+3 tergabung); pemicu palsu 0.
- F3 WER pilot (`results/asr_pilot_MSI_20261112_041011.md`, n=36, P01 dibaca): faster GPU+prompt 38,75% (formal 33,77 / semi 39,02 / informal 43,21), faster GPU tanpa prompt 56,25%, openai GPU+prompt 39,58%, openai tanpa prompt 57,50%, faster CPU int8+prompt 39,58% (0,928 s), openai CPU fp32+prompt 39,58% (2,146 s).
- F9 uji coba pilot (`results/eval_pilot_MSI_20261112_042305.md`, n=36): waktu respons Qwen GPU 2,496 ± 0,407 s (total komputasi 1,384 ± 0,433), CPU 4,880 ± 1,205 s (maks 9,497); WER GPU utuh 38,75% / vad 35,00%; EM vad GPU: Qwen 44,44, rule 63,89, IndoBERT 55,56; intent vad GPU: 80,56 / 69,44 / 91,67.
- **F9 set uji** (`results/eval_dataset_MSI_20261112_095743.md`, n=162): waktu respons Qwen GPU 2,424 ± 0,528 s (maks 4,34), CPU 5,368 ± 2,791 s (maks 26,04); total komputasi GPU 1,300 ± 0,604. WER GPU utuh 31,44% / vad 30,78%. Intent/EM GPU teks: Qwen 75,31/65,43, rule 85,80/85,19, IndoBERT 96,30/85,19; vad: 62,96/45,68, 65,43/61,11, 83,95/56,17. CPU teks Qwen 78,40/70,99. H1 Qwen formal+semi: GPU vad 62,04%, teks 78,70%.
- F9 analisis (`results/analisis_dataset_MSI_20261112_104423.md`): Qwen combined_command F1 0,07 (teks); McNemar intent IndoBERT > Qwen p < 0,001 semua masukan; Qwen GPU vs CPU JSON berbeda 13/162 (teks), EM CPU > GPU p = 0,004.
