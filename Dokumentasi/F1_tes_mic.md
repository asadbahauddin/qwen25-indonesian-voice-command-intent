# F1 — Uji Mikrofon (wireless lavalier)

**Tanggal:** 11 November 2026 · **Perangkat:** laptop MSI, receiver USB `Microphone (USBAudio1.0)` (VID_4C4A PID_4155)
**Bukti:** [F1_bukti_tes_mic.txt](F1_bukti_tes_mic.txt), [F1_bukti_tes_mic.png](F1_bukti_tes_mic.png), `results/mic_MSI_20261111_222034.{md,json}`
**Skrip:** `bench/tes_mic.py`, `src/audio_io.py` · **Konfigurasi:** `config.yaml` (`audio`, `levels`, `bench`)

## Tujuan
Memastikan mikrofon menghasilkan audio **16 kHz mono 16-bit** yang layak untuk Silero VAD dan Whisper,
serta mengukur level, clipping, dan SNR pada tiga kondisi: diam, bicara normal, dan bicara keras.

## Metode
1. Receiver dibuka di sample rate native-nya, yaitu **48 kHz via WASAPI**. Perangkat tidak dipaksa membuka 16 kHz.
2. Sinyal di-downmix ke mono, lalu di-resample streaming ke 16 kHz dengan `soxr` kualitas HQ.
3. Setiap kondisi direkam 5 detik. Hasilnya disimpan sebagai WAV native dan WAV 16 kHz PCM_16.
4. Level (RMS, peak, persentil 90 RMS per jendela 100 ms) dihitung pada **sinyal 16 kHz**, karena sinyal inilah yang dipakai VAD dan ASR.
5. Clipping (|x| ≥ 0,999) dan "sentuh limiter" (|x| ≥ 0,98) dihitung pada **sinyal native**. Alasannya, resampling bisa menimbulkan *overshoot* di atas 1,0 pada sinyal yang mendekati batas, sehingga muncul clipping semu.
6. SNR = RMS p90 kondisi ucapan − RMS total rekaman diam.

## Hasil (rekaman 11 Nov 2026 22:20, `results/mic_MSI_20261111_222034.md`)
| Kondisi | RMS (dBFS) | Peak (dBFS) | RMS p90 jendela (dBFS) | Clip native | Sentuh limiter | Overshoot 16k |
|---|---|---|---|---|---|---|
| diam | -90,94 | -71,22 | -88,30 | 0 | 0 | 0 |
| normal | -17,35 | -0 | -13,21 | 0 | 53 | 1 |
| keras | -13,34 | 0 | -7,87 | 0 | 101 | 2 |

- Format WAV 16 kHz terverifikasi: 16000 Hz, 1 kanal, PCM_16, durasi 5,000 s.
- SNR terhitung 77,73 dB (normal) dan 83,07 dB (keras), tetapi **tidak representatif** (lihat temuan 2).

## Temuan
1. **Tidak ada clipping sungguhan.** Puncak ucapan berulang kali tertahan tepat di bawah 0 dBFS. Ini menandakan transmitter memiliki **limiter otomatis**. "Clipping" 1–2 sampel yang muncul pada versi 16 kHz adalah overshoot akibat resampling.
2. **Ada noise gate di perangkat.** Saat diam, sinyalnya ±-91 dBFS, nyaris sunyi digital. Jadi noise ruangan yang sebenarnya **tidak dapat diukur** dengan perangkat ini, dan SNR tidak boleh dilaporkan sebagai SNR akustik.
   - Konsekuensi untuk F2 (VAD): awal dan akhir kata yang lemah berpotensi ikut terpotong oleh gate. Ini dicatat sebagai keterbatasan perangkat.
3. **Level ucapan tinggi.** RMS p90 ucapan normal -13 dBFS, padahal target nyaman sekitar -20 dBFS. Penyebabnya posisi mic dekat mulut dan suara penutur yang keras. Untuk perekaman dataset, mic dipasang sekitar 20 cm di bawah mulut, dan volume input Windows diturunkan bila ucapan keras sampai clipping.

## Riwayat percobaan (masalah yang ditangani)
| Waktu | Hasil | Tindakan |
|---|---|---|
| 22:08 | Semua kondisi -200 dBFS (sinyal nol mutlak) di WASAPI, MME, dan WDM-KS | Transmitter belum terhubung. Setelah transmitter dicek, sinyal kembali. Hasil tidak valid dan dihapus. |
| 22:16 | Keras: 39 sampel clipping native; rekaman "diam" berisi suara | Gain/posisi mic disesuaikan, rekaman diam diulang dengan benar-benar sunyi |
| 22:20 | Tidak ada clipping native; diam bersih | **Dipakai sebagai hasil F1** |

Perbaikan perangkat lunak selama F1:
- durasi 16 kHz dipotong tepat 5,000 s, sebelumnya 5,024 s karena sisa resampler;
- hitungan blok terbuang di-reset saat menunggu Enter;
- clipping diukur pada sinyal native;
- ditambah opsi `--from` untuk menganalisis ulang rekaman.

## Cara menjalankan
```powershell
& "C:\Users\indie\.conda\envs\mbkm-nlu\python.exe" bench\tes_mic.py --list     # daftar perangkat
& "C:\Users\indie\.conda\envs\mbkm-nlu\python.exe" bench\tes_mic.py            # uji lengkap (tekan Enter tiap kondisi)
& "C:\Users\indie\.conda\envs\mbkm-nlu\python.exe" bench\tes_mic.py --from 20261111_222034   # analisis ulang
```

## Kalimat logbook
> Menguji mikrofon wireless lavalier (48 kHz → 16 kHz mono 16-bit via soxr) pada kondisi diam, normal, dan keras; tidak ada clipping pada sinyal asli, terdeteksi limiter dan noise gate bawaan transmitter, dan rekaman 16 kHz terverifikasi siap untuk VAD dan Whisper.
