# F8 — Transkrip, label final, dan cek kebocoran dataset responden

**Tanggal:** 12 November 2026 · **Status:** alat siap. Transkrip R01 terkoreksi (54/162), label 0/162.

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
