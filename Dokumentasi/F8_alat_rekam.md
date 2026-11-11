# F8 — Alat Perekaman Dataset Responden (kalimat bebas)

**Tanggal:** 11 November 2026 · **Status:** alat siap, perekaman belum dimulai
**File:** `bench/rekam_dataset.py`, `bench/buat_skenario.py`, `bench/skenario_dataset.json` (v1), `config.yaml` (bagian `dataset`), `Dokumentasi/F8_lembar_persetujuan.md`, `Dokumentasi/F8_data_card.md`

## Desain (disetujui peneliti 11 Nov 2026)
- Responden **berbicara langsung ke mikrofon** dengan **kalimat sendiri** berdasarkan kartu skenario. Kalimat tidak dibacakan. Ini sesuai judul penelitian ("perintah kalimat bebas") dan membuat data uji **independen** dari set pilot, data latih, dan kamus rule-based (lihat ancaman validitas di F6).
- Rekaman diuji untuk ketiga metode, dengan dua masukan: transkrip manual (ground-truth) dan transkrip Whisper.
- Rencana (diperbarui 11 Nov): **3 responden** (peneliti + 2 orang) × **54 kartu** = **162 ujaran**, sesuai rentang 150–250 di proposal.
- Peneliti juga menjadi responden. Ini **keterbatasan**: peneliti sudah mengenal sistem dan kalimat pilot, sehingga gaya kalimatnya bisa terpengaruh. Hasil akan dilaporkan juga per responden.

## Kartu skenario (`bench/skenario_dataset.json` v2; daftar cetak: `Dokumentasi/F8_daftar_kartu_skenario.md`)
| Item | Nilai |
|---|---|
| Jumlah | 54 kartu = 6 intent × 9 (v1 = 48 kartu, ditambah agar total ≥ 150 ujaran) |
| Formalitas | formal 18, semi-formal 18, informal 18 |
| Cakupan entity | semua ruangan (7/7), benda (7/7), orang (5/5), dan dokumen (5/5) muncul |
| Isi kartu | **Tujuan** (contoh: "Minta robot pergi ke LAB OTOMASI.") + **gaya** (formal/semi-formal/informal). Tidak ada contoh kalimat. |
| Perintah gabungan | Ditulis netral "(1) …; (2) …" agar tidak memancing kata penghubung tertentu. Ada 1 kartu dengan kata ganti ("orang yang sama, boleh pakai 'beliau'/'dia'"). |
| Urutan | Diacak per responden (seed dari kode responden) untuk mengurangi efek urutan |

## Alat rekam (`bench/rekam_dataset.py`)
- **Push-to-talk:** tekan Enter untuk mulai, Enter lagi untuk berhenti, dengan tambahan 300 ms supaya ujung kata tidak terpotong. Rekaman berhenti otomatis setelah 15 s.
- Setiap rekaman langsung dicek: durasi < 0,6 s, puncak < -30 dBFS, atau clipping pada sinyal native akan memunculkan peringatan dan saran ulang.
- Pilihan setelah merekam: simpan & lanjut / **u**lang / **p**utar / **s** lewati / **q** keluar. Perekaman bisa dilanjutkan karena item yang sudah tersimpan dilewati.
- **Mode skenario** → `dataset/<kode>/<kode>_Sxx.wav`, `dataset/metadata.csv`, `dataset/responden.csv`. Data responden (usia, jenis kelamin, bahasa ibu, persetujuan) diminta sekali per responden. Perekaman ditolak bila persetujuan belum ditandatangani.
- **Mode baca** (pilot) → `recordings/pilot_audio/<kode>/`. Transkrip dan label langsung diambil dari kalimat yang dibaca.
- Kolom metadata: penutur, mode, urutan, item, formalitas, target intent/JSON, tujuan/teks, wav, durasi, puncak, RMS, clipping, take, waktu, perangkat, transkrip, label final, status label, catatan.

## Uji fungsi (input simulasi, 11 Nov 2026 23:08)
Alur mode baca berjalan: WAV tersimpan 16000 Hz / 1 kanal / PCM_16 dan metadata tertulis. Saat uji, mic sedang tidak mengirim sinyal (-200 dBFS), dan peringatan "terlalu pelan / mic mati?" muncul dengan benar. Data uji sudah dihapus.

## Privasi dan HKI
- Folder `dataset/` **tidak di-push** ke GitHub (repo publik). Simpan cadangan di Google Drive pribadi.
- Nama responden hanya ada di lembar persetujuan kertas; rekaman memakai kode R01, R02, …
- Lembar persetujuan: `Dokumentasi/F8_lembar_persetujuan.md` (cetak 1 per responden). Templat data card untuk HKI: `Dokumentasi/F8_data_card.md`.

## Cara menjalankan
```powershell
$PY = "C:\Users\indie\.conda\envs\mbkm-nlu\python.exe"
& $PY bench\rekam_dataset.py --mode baca --penutur P01        # Anda membacakan 36 kalimat pilot
& $PY bench\rekam_dataset.py --mode skenario --penutur R01    # responden 1 (kalimat bebas)
```

## Kalimat logbook
> Menyusun 54 kartu skenario perintah (6 intent × 9, formalitas seimbang) dan alat perekaman push-to-talk dengan pemeriksaan kualitas otomatis, metadata, lembar persetujuan responden, serta templat data card untuk pendaftaran HKI dataset.
