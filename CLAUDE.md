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
- **Target:** Raspberry Pi 5 8GB + Active Cooler, fully offline. (Sempat tertunda: microSD rusak → OS gagal boot.)
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
| F9 | Evaluasi penuh: WER, EM, F1, confusion matrix, teks vs transkrip, laptop vs RPi 5 |
| F10 | Bahan luaran: grafik untuk artikel/poster, paket dataset + data card untuk HKI |

## Status Proyek
> Diperbarui oleh Claude Code di akhir setiap fase. Format: fase | status | bukti (file/commit) | catatan.
> **Audit terakhir: 11 Nov 2026 (sesi baru, riwayat chat lama hilang).**

| Fase | Status | Bukti | Catatan |
|---|---|---|---|
| F0 | **Selesai** (ulang 11 Nov) | `environment.yml`, `Dokumentasi/F0_lingkungan.md`, `Dokumentasi/F0_bukti_cek_env.{txt,png}` | Env conda `mbkm-nlu` (Py 3.11.18), torch 2.14.1+cu126 CUDA True, ctranslate2 4.8.2 CUDA, Ollama 0.30.6 + `qwen2.5:1.5b`. `.venv` lama (rusak) dihapus. |
| F1 | **Selesai** (11 Nov) | `bench/tes_mic.py`, `results/mic_MSI_20261111_222034.{md,json}`, `Dokumentasi/F1_tes_mic.md` | WASAPI 48 kHz → mono 16 kHz PCM_16 terverifikasi. Tidak ada clipping native. Transmitter punya **limiter + noise gate** (diam ±-91 dBFS), sehingga SNR akustik tidak terukur. Level ucapan normal p90 -13 dBFS (tinggi). |
| F2 | Belum | – | Tidak ada `src/vad.py`, `bench/tes_vad.py`, `recordings/seg_*.wav`. |
| F3 | Belum | – | Tidak ada `src/asr.py`. |
| F4 | Belum | – | Tidak ada `src/nlu/`, `prompts/` kosong. Model `qwen2.5:1.5b` sudah ter-pull di Ollama. |
| F4b | Belum | – | Tidak ada `rule.py`, `indobert.py`, `config/keywords_id.yaml`, `data/`, `models/`. Screenshot `Dokumentasi/*.png` bukan bukti hasil (hanya tangkapan file explorer). |
| F5 | Belum | – | Tidak ada `src/pipeline.py`, `src/cli.py`. |
| F6 | Persiapan | `bench/pilot_set.json`, `Dokumentasi/lembar_baca_pilot.md` (commit `90c8f2d`) | 36 kalimat berlabel (6 intent × 3 formalitas × 2). Belum ada `bench/uji_llm.py` dan hasil. |
| F7 | Belum | – | Tidak ada bukti RPi 5. |
| F8 | Belum | – | Tidak ada alat rekam dataset, `dataset/` tidak ada. |
| F9 | Belum | – | – |
| F10 | Belum | – | – |

**Keputusan teknis yang sudah diambil:**
- Audio ditangkap pada sample rate native perangkat, downmix mono, lalu di-resample streaming ke 16 kHz dengan `soxr.ResampleStream` kualitas HQ (`src/audio_io.py`, `config.yaml: audio`).
- Konfigurasi terpusat di `config.yaml`; log ke `logs/<nama>_<host>_<tanggal>.log` (`src/utils.py`).
- Lingkungan: conda `mbkm-nlu` + pip (versi ter-pin), PyTorch 2.14.1+cu126. CUDA toolkit sistem (11.2/11.8/12.1) dibiarkan; faster-whisper memakai `cublas64_12.dll` (v12.1) dan `cudnn64_9.dll` (v11.8), jadi **CUDA 11.8 jangan dihapus**. Cache pip laptop sengaja dinonaktifkan.
- Mic: receiver wireless lavalier `USBAudio1.0` (USB VID_4C4A PID_4155). Jangan pakai input "NVIDIA Broadcast" karena audionya diolah.
- F1: capture WASAPI 48 kHz (bukan dipaksa 16 kHz). Clipping diukur pada sinyal native, karena resampling soxr menimbulkan overshoot semu. Transmitter lavalier memakai limiter dan noise gate: SNR dari rekaman diam tidak boleh dilaporkan sebagai SNR akustik. Pre-roll VAD di F2 tidak bisa mengembalikan audio yang sudah dipotong gate.
- Kosakata domain lab (ruangan/benda/orang/dokumen) ada di `config/domain_id.yaml`. "Trainer RL" = trainer Rangkaian Listrik; ejaan "Pak Andi".
- Usulan skema `combined_command`: field tingkat atas null, sub-perintah di `steps[]` (menunggu persetujuan peneliti).
- Rencana responden: 4 orang × 48 kalimat = 192 sampel.
- Belum diputuskan: faster-whisper vs openai-whisper, threshold VAD, versi system prompt.

**Angka yang sudah terukur:**
- F1 mic (`results/mic_MSI_20261111_222034.md`): diam RMS -90,94 dBFS; normal RMS -17,35 / p90 -13,21 dBFS; keras RMS -13,34 / p90 -7,87 dBFS; clipping native 0 untuk semua kondisi.
- Belum ada metrik NLU/ASR/latency.
