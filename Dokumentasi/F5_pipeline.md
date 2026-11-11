# F5 — Integrasi pipeline + CLI interaktif + log CSV

**Tanggal:** 12 November 2026 · **Status:** selesai (uji fungsi). Angka latency di sini hanya **uji asap** (n = 1–6, satu file); angka laporan diukur di F9.

## File
| File | Isi |
|---|---|
| `src/pipeline.py` | Kelas `Pipeline`: VAD → Whisper → NLU (1–3 metode), `from_text`, `from_audio`, `from_file`; log CSV per ujaran × metode |
| `src/cli.py` | CLI interaktif (`rich`): ganti metode/mode/Whisper/beam/perangkat tanpa restart |
| `src/utils.py` → `ram_tersedia_gb()` | RAM tersedia tanpa pustaka tambahan (Windows `GlobalMemoryStatusEx`, Linux `/proc/meminfo`) |
| `config.yaml` → `pipeline` | perangkat awal, metode awal, mode, simpan audio, prefiks log CSV, pemanasan |
| `config.yaml` → `nlu.qwen.num_gpu` | 99 = semua layer di GPU, 0 = paksa CPU |
| `logs/pipeline_<host>_<tanggal>.csv` | log per ujaran × metode (lokal, tidak di-push) |
| `results/cli_<host>_<ts>.{md,json}` | ringkasan sesi dari `/simpan` |

## Cara menjalankan
```powershell
$PY = "C:\Users\indie\.conda\envs\mbkm-nlu\python.exe"
& $PY -m src.cli                                  # mode teks, metode qwen (config.yaml: pipeline)
& $PY -m src.cli --mode mic --metode semua        # mikrofon (receiver lavalier), ketiga metode
& $PY -m src.cli --perangkat cpu                  # skenario laptop tanpa GPU
& $PY -m src.cli --mic "Microphone Array"         # uji dengan mic bawaan laptop
```
Perintah di dalam CLI: `/metode qwen|rule|indobert|semua` · `/mode mic|teks` · `/whisper base|small [--unduh]` · `/beam <n>` · `/perangkat gpu|cpu` · `/file <wav>` · `/stat` · `/reset` · `/simpan` · `/bantuan` · `/keluar`. Pada mode teks, kalimat yang diketik langsung diproses.

Setiap perintah menampilkan:
- transkrip;
- JSON per metode (bingkai hijau bila valid);
- tabel latency: `t_vad`, `t_asr`, `t_nlu`, `t_total`, `t_respons`, dan khusus Qwen `load`/`prompt_eval`/`eval`/`tok/s`;
- status: metode, mode, Whisper, beam, perangkat, RAM tersedia, dan suhu CPU (hanya di Linux).

## Definisi latency (penting untuk laporan)
| Kolom | Arti |
|---|---|
| `t_vad` | waktu **komputasi** Silero untuk frame ujaran |
| `t_tunggu_vad` | jeda diam yang ditunggu VAD sebelum ujaran dinyatakan selesai (≈ `min_silence`, 0,8 s) |
| `t_asr`, `t_nlu` | waktu komputasi Whisper dan metode NLU |
| `t_total` | `t_vad + t_asr + t_nlu` → kolom "Total" tabel laporan |
| `t_respons` | `t_tunggu_vad + t_asr + t_nlu` → waktu yang dirasakan pengguna setelah selesai bicara |

Kedua jenis total ini dipisah karena jeda tunggu VAD bukan beban komputasi, tetapi tetap dirasakan pengguna. Hipotesis H3 (< 15 s) dilaporkan untuk keduanya.

## Keputusan teknis
1. **Model dimuat sekali, metode dimuat saat pertama dipakai**, lalu diberi **pemanasan realistis**: kalimat majemuk untuk NLU, dan 3 s derau lemah untuk Whisper (diam total membuat Whisper melewatkan dekode, sehingga pemanasan menjadi semu). Panggilan pertama tanpa pemanasan yang memadai di CPU: Whisper 11,4 s dan Qwen 9,4 s; panggilan berikutnya ±4 s dan ±3,5 s.
2. **`num_gpu` Ollama wajib eksplisit.** Temuan: setelah runner CPU (`num_gpu 0`) dimuat, permintaan *tanpa* `num_gpu` tetap dijalankan di CPU (`/api/ps` size_vram = 0). Mode GPU diam-diam berjalan di CPU. Sekarang GPU = `num_gpu 99` (semua layer) dan CPU = `0`. Dicek pada urutan GPU → CPU → GPU: VRAM 1,1 GB → 0 → 1,1 GB.
3. **Bug thread pustaka silero-vad.** `silero_vad/model.py` memanggil `torch.set_num_threads(1)` saat *import*. Pengaturan ini global, sehingga IndoBERT di CPU ikut terkunci 1 thread. `SileroVAD` sekarang mengembalikan jumlah thread semula pada mode ONNX (sesi ONNX silero sudah 1 thread sendiri). IndoBERT CPU: 0,38 → 0,17 s. Hasil F4b/F6 tidak terdampak, karena `bench/uji_llm.py` tidak meng-import silero dan IndoBERT di sana berjalan di GPU.
4. **Mode file** (`/file`, `from_file`): VAD disimulasikan sebagai streaming dan segmennya disambung, sama dengan analisis F2. Akan dipakai F9 untuk masukan "segmen VAD".
5. **Mode mic:** setelah satu ujaran diproses, antrean audio dibuang (`drain`) dan VAD di-reset, supaya suara yang masuk selama pemrosesan tidak menumpuk. Setiap ujaran disimpan ke `recordings/cli/` (lokal).
6. **`/whisper small`** tidak mengunduh diam-diam. Model belum ada di `models/whisper`, jadi diperlukan `--unduh` sebagai persetujuan eksplisit.
7. **Mic tidak tersedia** (receiver tidak tercolok): CLI memberi pesan lalu kembali ke mode teks, tidak crash.

## Bukti uji (laptop MSI, i5-12450H, RTX 2050, RAM 7,7 GB)
Masukan uji: 3 kalimat **pilot** (set pengembangan) dan rekaman uji mic F1 `recordings/mic_normal_MSI_20261111_222034_16k.wav`. **Data responden (set uji) tidak dipakai.**

Contoh masukan audio, ketiga metode, GPU (`results/cli_MSI_20261112_033222.md` + run 03:33):

| Metode | t_vad | t_asr | t_nlu | t_total | t_respons |
|---|---|---|---|---|---|
| qwen | 0,034 | 0,167 | 0,695 | 0,897 | 1,663 |
| rule | 0,034 | 0,167 | 0,001 | 0,202 | 0,968 |
| indobert | 0,034 | 0,167 | 0,018 | 0,220 | 0,986 |

Mode CPU, 6 ulangan pada file yang sama, setelah perbaikan thread: Whisper 2,08 ± 0,33 s, Qwen 3,65 ± 1,33 s, IndoBERT 0,166 ± 0,098 s. Transkrip dan JSON identik di setiap ulangan (deterministik).

`results/cli_MSI_20261112_031314.md` adalah uji **sebelum** perbaikan pemanasan, `num_gpu`, dan thread. Angkanya tidak dipakai.

## Masalah dan ancaman validitas
1. **RAM laptop 7,7 GB hampir penuh.** RAM tersedia hanya ±0,8 GB bahkan sebelum CLI dijalankan (VS Code, Arduino IDE, dll.; Windows Memory Compression 1,7 GB). Akibatnya ada lonjakan acak 20–27 s, misalnya Qwen GPU `load_s` 26 s tanpa reload runner. **Untuk pengukuran F9:** tutup aplikasi lain, laptop dicolok listrik, dan buang beberapa ujaran awal sebagai pemanasan. `ram_tersedia_gb` dicatat per baris CSV agar ujaran yang terkena swap bisa dikenali.
2. Mode CPU memakai CPU yang sama untuk Whisper, Qwen (Ollama), dan IndoBERT secara berurutan. Ini mewakili "laptop tanpa GPU", **bukan** Raspberry Pi 5.
3. Transkrip contoh ("deretan laporan kasi tunggu ke ruang dosisi") menunjukkan galat Whisper base merambat ke NLU (ketiga metode memberi intent berbeda). Inilah alasan F9 menguji NLU pada teks ground-truth *dan* pada transkrip.

## Kalimat logbook
> Mengintegrasikan VAD, Whisper, dan tiga metode NLU ke dalam satu pipeline dengan CLI interaktif dan log CSV, serta memperbaiki dua sumber galat pengukuran (Ollama tetap berjalan di CPU setelah mode CPU, dan pustaka Silero mengunci PyTorch ke 1 thread).
