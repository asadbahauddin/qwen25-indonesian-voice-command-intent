# Data Card — Dataset Perintah Suara Robot Bahasa Indonesia (Kalimat Bebas)
*(Templat. Bagian bertanda ⟨…⟩ diisi otomatis atau manual setelah perekaman selesai, sebelum pengajuan HKI.)*

## 1. Ringkasan
| Item | Isi |
|---|---|
| Nama | Dataset Perintah Suara Robot Layanan Laboratorium — Bahasa Indonesia (formal, semi-formal, informal) |
| Versi | v1 ⟨tanggal rilis⟩ |
| Pembuat | As'ad Bahauddin Ahmad; Ir. Vivi Tri Widyaningrum, S.Kom., M.T. — Teknik Mekatronika, Universitas Trunojoyo Madura |
| Pendanaan / program | Asistensi Hibah Penelitian (MBKM Riset), LPPM UTM 2026 |
| Tujuan | Evaluasi ekstraksi intent dan entity perintah suara kalimat bebas untuk robot layanan (ASR + NLU) |
| Lisensi | ⟨mis. CC BY-NC 4.0, sesuai keputusan tim/LPPM⟩ |

## 2. Isi
| Item | Isi |
|---|---|
| Jumlah responden | ⟨n⟩ (rencana 3: peneliti + 2 responden) |
| Jumlah ujaran | ⟨n⟩ (rencana 3 × 54 = 162) |
| Durasi total | ⟨menit⟩ |
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
4. ⟨Pemeriksa kedua / kesepakatan antar-anotator, bila ada⟩

## 5. Pemisahan data dan anti-kebocoran
Tidak ada kalimat yang sama dengan set pilot (`bench/pilot_set.json`), data latih IndoBERT (`data/indobert_train.jsonl`), maupun contoh di prompt Qwen (dicek otomatis setelah transkripsi). Dataset ini **hanya** dipakai sebagai data uji. Tidak dipakai untuk melatih atau menyetel metode apa pun.

## 6. Etika dan privasi
Setiap responden menandatangani lembar persetujuan (`Dokumentasi/F8_lembar_persetujuan.md`). Nama hanya tercantum di lembar kertas tersebut. Audio tidak diunggah ke repositori publik.

## 7. Keterbatasan
- Jumlah responden kecil (⟨n⟩); variasi dialek dan usia terbatas.
- Salah satu responden adalah peneliti sendiri, yang mengenal sistem (potensi bias gaya kalimat).
- Satu jenis mikrofon dan satu ruangan.
- Noise gate dan limiter transmitter memengaruhi bagian sunyi dan puncak sinyal.
- Kosakata entity terbatas pada lingkungan Lab Sistem Otomasi UTM.

## 8. Statistik
⟨Diisi otomatis di F10: jumlah per intent/formalitas/responden, durasi rata-rata, distribusi panjang kalimat.⟩
