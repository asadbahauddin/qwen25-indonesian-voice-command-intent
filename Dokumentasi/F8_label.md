# F8 — Transkrip, label final, dan cek kebocoran dataset responden

**Tanggal:** 12 November 2026 · **Status:** selesai. Transkrip 162/162 terkoreksi, label 162/162 final, cek kebocoran akhir dijalankan.

## Alur
1. **Koreksi transkrip** (`bench/koreksi_transkrip.py`): audio diputar dan dua draf Whisper ditampilkan. Penilai menulis transkrip yang benar.
2. **Label final** (`bench/label_dataset.py`): drafnya diambil dari target kartu. Penilai mengonfirmasi atau mengubahnya sesuai yang benar-benar diucapkan.
3. **Cek kebocoran** (`bench/cek_kebocoran.py`): transkrip dibandingkan dengan pilot, data latih IndoBERT, dan contoh prompt Qwen.
4. **Evaluasi** (`bench/evaluasi.py --data dataset`): memakai item berstatus `final` saja.

```powershell
$PY = "C:\Users\indie\.conda\envs\mbkm-nlu\python.exe"
& $PY bench\koreksi_transkrip.py --penutur R02
& $PY bench\label_dataset.py --penutur R01
& $PY bench\cek_kebocoran.py
```

## Konvensi transkrip
Kata yang diucapkan ditulis apa adanya, termasuk partikel dan kata gaul. Bunyi ragu (eh, em) tidak ditulis. Nama mengikuti kamus, dan angka ditulis dengan huruf.

**Kata depan ditulis terpisah (EYD)**: "ke ruang dosen", "ke lengan robot". Temuan 12 Nov: 11/54 transkrip R01 memakai bentuk tersambung ("keruang", "kelengan", "kemesin", "ketrainer"), 3 di antaranya berasal dari draf Whisper yang diterima apa adanya. Alat koreksi sekarang memperingatkan bentuk itu (juga pada draf 1/2) dan mengusulkan bentuk EYD. **Keputusan peneliti (12 Nov):** ke-11 transkrip R01 dipisahkan otomatis (`ke ruang`, dst.), dan R01_S07 "andu" dikoreksi menjadi "andi" (salah ketik). Cadangan: `dataset/metadata.bak_20261112_044408.csv`; perubahan dicatat di `catatan` (`rapikan=EYD-kata-depan`).

## Prinsip label
- Label menggambarkan **apa yang diucapkan** (transkrip), **bukan isi kartu**:
  - entity yang tidak disebut → null;
  - entity lain yang disebut → entity itu;
  - dua tindakan → `combined_command`.
- **Draf = target kartu**, bukan keluaran Qwen, rule-based, atau IndoBERT. Dengan begitu label tidak berpihak ke salah satu metode yang sedang dibandingkan.
- Label dinormalisasi ke nama kanonik `config/domain_id.yaml` dan wajib lolos skema v2. Nilai di luar kamus harus dikonfirmasi.
- Petunjuk "entity tidak ditemukan di transkrip" (berbasis alias kamus) hanya untuk menarik perhatian penilai; keputusannya tetap di tangan penilai.
- Sumber label dicatat di kolom `catatan`: `label=target`, `ubah`, atau `json`. Jumlah label yang berbeda dari target kartu dilaporkan.

## Cek kebocoran (aturan ditetapkan sebelum dijalankan)
- Ambang "mirip": Jaccard token ≥ 0,8.
- Laporan hanya memuat ID dan skor; kalimat responden tidak ditulis ke `results/` karena repo publik.

Hasil R01 (`results/kebocoran_MSI_20261112_044132.md`, n = 54):

| Pembanding | Sama persis | Mirip | Jaccard maks |
|---|---|---|---|
| Pilot | 0 | 0 | 0,57 |
| Data latih IndoBERT | 0 | 0 | 0,75 |
| Contoh prompt Qwen | 0 | 0 | 0,71 |

Cek ini dijalankan ulang setelah seluruh transkrip selesai.

## Hasil akhir (12 Nov 2026)
- **Transkrip 162/162.** Sumber akhir per item: ketik 118, draf 1 41 (termasuk 2 yang dikonfirmasi peneliti), draf 2 3.
- **Perbaikan setelah pemeriksaan otomatis** (semua dicadangkan di `dataset/metadata.bak_*.csv` dan dicatat di `catatan`):
  - 11 kata depan tersambung di R01 dan 1 di R03 (`ke-trainer`) dipisahkan sesuai EYD.
  - R01_S07: "andu" dikoreksi menjadi "andi".
  - R02_S53 dan R03_S02 tersimpan sebagai "1/2" dan "y" karena petunjuk alat yang membingungkan ("1/2=draf benar"). Peneliti mengonfirmasi bahwa maksudnya "kedua draf benar", sehingga diisi dengan draf 1. Ketiga konfigurasi Whisper sepakat pada kalimat yang sama. Petunjuk alat diperbaiki, dan masukan berupa angka atau "/" sekarang ditolak.
- **Label 162/162 final.** 161 sama dengan target kartu, 1 diubah: R02_S29 "antarkan berkas ini ke ruang dosen" → `document = null`, karena jenis berkas tidak diucapkan (keputusan peneliti).
- **Variasi nama yang diucapkan, label tetap kanonik:** "bapak Kusairi" → `pak kus` (R03_S20, S25, S41), "lembaran nilai" → `lembar nilai`, "tugas akhir" → `berkas tugas akhir`. **Kamus domain tidak ditambah** (misalnya alias "kusairi"), karena itu sama dengan menyetel metode memakai set uji.

## Cek kebocoran akhir (`results/kebocoran_MSI_20261112_095154.md`, n = 162)
| Pembanding | Sama persis | Mirip (≥ 0,8) | Jaccard maks |
|---|---|---|---|
| Pilot | 0 | 0 | 0,62 |
| Data latih IndoBERT | 0 | 1 (R03_S46 ↔ T254, 0,83) | 0,83 |
| Contoh prompt Qwen | 0 | 1 (R03_S16 ↔ contoh 2, 0,83) | 0,83 |

Keduanya perintah pendek yang wajar di domain dengan kosakata terbatas ("robot pergi ke trainer sistem digital", "robot kembali ke posisi semula"); responden tidak pernah melihat data latih maupun prompt. **Keputusan peneliti:** analisis utama tetap memakai 162 item, ditambah **uji sensitivitas** tanpa kedua item tersebut (n = 160) melalui `bench/evaluasi.py --sensitivitas`.
