# F0 — Penyiapan Lingkungan Pengembangan (ulang, conda)

**Tanggal:** 11 November 2026 · **Perangkat:** laptop MSI (Windows 11, RTX 2050 4 GB)
**Bukti:** [F0_bukti_cek_env.txt](F0_bukti_cek_env.txt), [F0_bukti_cek_env.png](F0_bukti_cek_env.png), `results/env_MSI_20261111_220331.json` (lokal)

## Latar belakang
F0 pertama (9 Okt 2026, commit `003c3b5`) memakai **venv** yang dibuat dari env conda `py311-base`.
Env dasar itu kemudian terhapus, sehingga `.venv` tidak bisa dijalankan
(`No Python at ...\py311-base\python.exe`). Sesuai `CLAUDE.md`, lingkungan dipindah ke **conda**.

## Langkah yang dikerjakan
| No | Langkah | Perintah |
|---|---|---|
| 1 | Cek CUDA yang sudah terpasang (tidak memasang ulang) | `nvcc --version`, cek `CUDA_PATH`, cari `cublas64_12.dll`, `cudnn64_9.dll` |
| 2 | Buat env conda dari conda-forge | `conda create -n mbkm-nlu -c conda-forge --override-channels python=3.11 pip` |
| 3 | Pasang PyTorch CUDA (versi ter-pin F0) | `pip install -r requirements-torch-cuda.txt` |
| 4 | Pasang pustaka proyek (versi ter-pin) | `pip install -r requirements.txt` |
| 5 | Verifikasi | `python bench/cek_env.py`, `pip check` |
| 6 | Ekspor env | `conda env export -n mbkm-nlu --no-builds > environment.yml` |
| 7 | Bersihkan sisa yang tidak terpakai | hapus `.venv` rusak, cache pip lama, `conda clean --all`, folder temp pip |

## Hasil (output asli)
| Item | Hasil |
|---|---|
| Python | 3.11.18 (env `mbkm-nlu`) |
| GPU | NVIDIA GeForce RTX 2050, 4096 MiB, driver 610.78 |
| PyTorch | 2.14.1+cu126, `torch.cuda.is_available()` = True, cuDNN 91002 |
| ctranslate2 (faster-whisper) | 4.8.2, 1 perangkat CUDA terdeteksi, compute type float16/int8 tersedia |
| Ollama | 0.30.6, model `qwen2.5:1.5b` (986 MB) tersedia |
| `pip check` | No broken requirements found |

## Keputusan teknis (untuk dipertanggungjawabkan)
1. **conda + pip:** conda mengelola Python dan pustaka sistem, sedangkan pip mengelola paket ML yang versinya di-pin. Env bisa dibuat ulang dengan `conda env create -f environment.yml`.
2. **CUDA toolkit sistem tidak disentuh.** Laptop sudah punya CUDA 11.2, 11.8, dan 12.1. PyTorch dari pip membawa runtime CUDA 12.6 sendiri. faster-whisper (ctranslate2) memakai `cublas64_12.dll` (CUDA 12.1) dan `cudnn64_9.dll` (di folder v11.8) yang sudah ada di PATH, jadi tidak ada paket `nvidia-*` tambahan.
3. **CUDA 11.8 tidak boleh dihapus** karena berisi `cudnn64_9.dll` yang dibutuhkan faster-whisper untuk GPU.
4. **Cache pip di laptop dinonaktifkan** (`global.no-cache-dir=true`), sehingga setiap pemasangan mengunduh ulang. Ini disengaja untuk menghemat disk.

## Pembersihan
| Item | Ukuran |
|---|---|
| `.venv` proyek (rusak) | 4,70 GB |
| Cache pip lama | 6,7 GB |
| Cache paket conda | 0,94 GB |
| Env conda `paklatif`, `robot-nlp`, `wake_word` (atas izin peneliti) | ±15 GB |

Ruang bebas drive C naik dari 39,0 GB menjadi 53,5 GB setelah pembersihan cache dan venv. Angka ini belum termasuk env yang sudah dihapus lebih dulu.

## Masalah yang ditemui
- Instalasi torch pertama macet selama 37 menit tanpa ada data yang terunduh. Prosesnya dihentikan, lalu diulang dengan `--timeout 60 --retries 10` dan berhasil (±2,6 GB).
- `git add` sekali gagal dengan *Permission denied* pada `.git/objects`. Kemungkinan file dikunci sementara oleh antivirus. Percobaan ulang berhasil.

## Cara menjalankan
```bash
conda activate mbkm-nlu
python bench/cek_env.py
```

## Kalimat logbook
> Menyiapkan ulang lingkungan pengembangan menggunakan conda (env `mbkm-nlu`, Python 3.11.18) dengan PyTorch 2.14.1 CUDA 12.6, faster-whisper 4.8.2, dan Ollama `qwen2.5:1.5b`; GPU RTX 2050 terverifikasi aktif dan konfigurasi diekspor ke `environment.yml`.
