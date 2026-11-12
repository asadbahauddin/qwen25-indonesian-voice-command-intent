# Data Card — Dataset Perintah Suara Robot Bahasa Indonesia (Kalimat Bebas)
*(Diisi 12 Nov 2026 dari `dataset/metadata.csv` melalui `luaran/statistik_dataset.py`. Versi laporan: Lampiran 7 laporan akhir.)*

## 1. Ringkasan
| Item | Isi |
|---|---|
| Nama | Dataset Perintah Suara Robot Layanan Laboratorium — Bahasa Indonesia (formal, semi-formal, informal) |
| Versi | v1.0 (tanggal rilis = tanggal unggah publik) |
| Pembuat | As'ad Bahauddin Ahmad; Ir. Vivi Tri Widyaningrum, S.Kom., M.T. — Teknik Mekatronika, Universitas Trunojoyo Madura |
| Pendanaan / program | Asistensi Hibah Penelitian (MBKM Riset), LPPM UTM 2026 |
| Tujuan | Evaluasi ekstraksi intent dan entity perintah suara kalimat bebas untuk robot layanan (ASR + NLU) |
| Lisensi | CC BY-NC 4.0 (Atribusi–NonKomersial). Rilis publik audio (mis. Kaggle) hanya setelah persetujuan tambahan responden (butir 5 lembar persetujuan) dan izin pencipta kedua. |

## 2. Isi
| Item | Isi |
|---|---|
| Jumlah responden | 3 (R01 perempuan 21 th, bahasa ibu Madura; R02 laki-laki 20 th, Jawa; R03 laki-laki 21 th, Jawa, peneliti) |
| Jumlah ujaran | 162 (54 per responden; 27 per intent; 54 per formalitas) |
| Durasi total | 13,4 menit; 4,98 ± 1,45 s per ujaran (2,78–10,78 s) |
| Format audio | WAV, 16 kHz, mono, PCM 16-bit (direkam 48 kHz lalu di-resample dengan soxr HQ) |
| Perangkat | Mikrofon wireless lavalier, receiver USB (VID_4C4A PID_4155), Windows WASAPI. Transmitter memiliki limiter dan noise gate bawaan. |
| Lingkungan | Laboratorium Sistem Otomasi, Teknik Mekatronika UTM (ruangan dalam, kondisi kebisingan normal) |
| Cara elisitasi | **Kalimat bebas**: responden diberi kartu skenario (tujuan + gaya bahasa) dan mengucapkan perintah dengan kata-kata sendiri. Kartu: `bench/skenario_dataset.json` v2 (54 kartu, 6 intent × 9, formalitas 18/18/18). |
| Label per ujaran | Transkrip manual, intent (6 kelas), entity (room/object/person/document), steps (perintah gabungan), formalitas, kode responden |
| Metadata responden | Usia, jenis kelamin, bahasa ibu (tanpa nama) |

## 3. Skema label
Lihat `src/nlu/base.py` (`COMMAND_SCHEMA_V2`). Intent: `navigate_room`, `navigate_object`, `find_person`, `deliver_document`, `combined_command`, `general_command`. Nilai entity kanonik: `config/domain_id.yaml`.

## 4. Proses pelabelan
1. Perekaman dengan `bench/rekam_dataset.py --mode skenario` (cek level otomatis, rekam ulang bila clipping atau terlalu pelan).
2. Draf transkrip dibuat dengan Whisper, lalu **diperiksa dan dikoreksi manual** oleh peneliti.
3. Label intent dan entity disusun dari transkrip final. `target` dari kartu hanya acuan; bila responden menyimpang dari kartu, label mengikuti ucapan sebenarnya.
4. Tidak ada anotator kedua; pelabelan oleh satu anotator (peneliti) dengan draf dari target kartu, bukan dari keluaran metode. 161/162 label sama dengan target kartu, 1 diubah (R02_S29). Ini dicatat sebagai keterbatasan.

## 5. Pemisahan data dan anti-kebocoran
Tidak ada kalimat yang sama dengan set pilot (`bench/pilot_set.json`), data latih IndoBERT (`data/indobert_train.jsonl`), maupun contoh di prompt Qwen (dicek otomatis setelah transkripsi). Dataset ini **hanya** dipakai sebagai data uji. Tidak dipakai untuk melatih atau menyetel metode apa pun.

## 6. Etika dan privasi
Setiap responden menandatangani lembar persetujuan (`Dokumentasi/F8_lembar_persetujuan.md`). Nama hanya tercantum di lembar kertas tersebut. Audio tidak diunggah ke repositori publik. Cadangan: arsip zip + `SHA256SUMS.txt` (checksum per file) di laptop peneliti (`backup/`) dan Google Drive pribadi.

## 7. Keterbatasan
- Jumlah responden kecil (3); variasi dialek dan usia terbatas (satu penutur berbahasa ibu Madura).
- Salah satu responden adalah peneliti sendiri, yang mengenal sistem (potensi bias gaya kalimat).
- Satu jenis mikrofon dan satu ruangan.
- Noise gate dan limiter transmitter memengaruhi bagian sunyi dan puncak sinyal. Clipping puncak sesaat terjadi pada 56/162 file (R01 13, R02 1, R03 42), maksimum 0,051% sampel per file, dan potongan datar terpanjang 6 sampel (0,38 ms) pada 16 kHz, sehingga tidak terdengar sebagai distorsi (`results/kualitas_dataset_MSI_20261112_005606.md`).
- Kosakata entity terbatas pada lingkungan Lab Sistem Otomasi UTM.

## 8. Statistik
- Per intent: 27 masing-masing; per formalitas: 54 masing-masing; per responden: 54 masing-masing.
- Panjang transkrip: 6,51 ± 2,70 kata (2–16), total 1055 kata.
- Entity terisi (tingkat atas): person 42, room 39, object 27, document 26; 27 combined_command masing-masing 2 langkah.
- Sumber transkrip akhir: diketik 118, draf 1 41, draf 2 3.
