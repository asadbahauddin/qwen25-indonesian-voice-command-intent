# F6 — Uji Pendahuluan Teks (pilot 36 kalimat × 3 metode)

**Tanggal:** 11 November 2026 · **Perangkat:** laptop MSI (RTX 2050), Ollama 0.30.6
**Bukti:** `results/summary_MSI_20261111_225631.md`, `results/uji_pilot_MSI_20261111_225631.{csv,json}`
**Skrip:** `bench/uji_llm.py` · **Data:** `bench/pilot_set.json` v1 · **Masukan:** teks ground-truth (tanpa ASR)
**Versi metode:** Qwen prompt v1 (sha `114d424e5d61`, schema aktif) · kamus rule-based v1 · IndoBERT `models/indobert_intent` (epoch 8)

## Tabel akurasi
| Metode | Jumlah kalimat uji | Intent Accuracy | Exact Match | F1 weighted | F1 macro | JSON valid |
|---|---|---|---|---|---|---|
| Qwen2.5 1.5B (Ollama) | 36 | 80,56% | 63,89% | 0,7931 | 0,7931 | 100% |
| Rule-based | 36 | 100,00% | 100,00% | 1,0000 | 1,0000 | 100% |
| IndoBERT (fine-tuned) | 36 | 100,00% | 100,00% | 1,0000 | 1,0000 | 100% |

## Per formalitas (Intent Accuracy / Exact Match, n = 12 per sel)
| Metode | formal | semi-formal | informal |
|---|---|---|---|
| Qwen2.5 | 83,3% / 75,0% | 91,7% / 66,7% | 66,7% / 50,0% |
| Rule-based | 100% / 100% | 100% / 100% | 100% / 100% |
| IndoBERT | 100% / 100% | 100% / 100% | 100% / 100% |

## Tabel latency (tahap NLU, masukan teks, laptop)
| Platform | VAD (s) | Whisper (s) | Qwen2.5 (s) | Total (s) |
|---|---|---|---|---|
| Laptop MSI (RTX 2050) | – | – | 0,786 ± 0,387 (n=36) | 0,786 ± 0,387 (n=36) |

Rule-based 0,0002 ± 0,0001 s; IndoBERT (GPU) 0,0174 ± 0,0240 s (n = 36).

Rincian Qwen: load 0,174 ± 0,018 s · prompt_eval 0,029 ± 0,011 s (923 token) · eval 0,561 ± 0,383 s (42,6 ± 28,6 token) · 76,2 ± 2,1 token/s. Nilai `load_s` ±0,17 s tetap muncul walaupun model sudah dimuat. Ini adalah *overhead* penjadwalan Ollama per permintaan, bukan pemuatan ulang model (pemuatan dingin 6–9 s).

## Analisis kesalahan Qwen (13 kalimat tidak Exact Match)
| Jenis kesalahan | Kalimat | Keterangan |
|---|---|---|
| **Struktur combined tidak konsisten** | P25, P26, P29 | `steps` sudah benar, tetapi intent tingkat atas ditulis `navigate_room` |
| Combined tidak dikenali | P30 | Kalimat informal dengan "trus" dan "dia" |
| Field tambahan / salah isi pada deliver | P20, P21, P22, P23 | Mis. `person` diisi nama dokumen, atau `room` ditambahkan padahal tujuannya orang |
| `steps` diisi pada intent non-combined | P35 | Melanggar aturan 1 di prompt |
| Salah intent pada informal | P24 ("laprak" dibaca "lapar praktikum"), P36 ("balik aja ke tempat semula") | Kosakata informal |
| Benda dianggap orang | P10 ("datangi trainer pneumatik") | |
| Kata ganti di combined | P28 | Langkah ke-2 menjadi navigate_object ke "laporan praktikum" |

Sebagian besar kesalahan Qwen adalah **pelanggaran aturan struktur** (intent tingkat atas vs `steps`, field yang seharusnya null). Skema v1 belum mengunci hal ini: `steps` boleh terisi pada intent apa pun.

## ⚠️ Ancaman validitas (wajib disebut di laporan)
Rule-based dan IndoBERT mendapat 100% **bukan bukti bahwa keduanya lebih baik dari Qwen**:
1. Set pilot, templat data latih IndoBERT, kamus rule-based, dan alias entity **disusun oleh pihak yang sama, pada sesi yang sama**, dengan kosakata dan pola kalimat yang mirip. Walaupun tidak ada kalimat yang identik (sudah dicek otomatis), pola kalimat pilot ikut terwakili di templat dan kamus.
2. Kalimat pilot masih "tertib": nama entity selalu persis seperti di kamus, dan kata penghubung selalu ada di daftar. Kalimat bebas dari responden kemungkinan besar tidak serapi itu.
3. Karena itu, hasil F6 hanya berfungsi sebagai **uji fungsi pipeline dan analisis kesalahan**, bukan pengujian hipotesis H1/H2. Pengujian hipotesis dilakukan di F9 pada dataset responden yang independen.

## Kesimpulan F6
- Pipeline evaluasi bekerja: semua metrik, confusion matrix, dan tabel laporan dihasilkan otomatis dari eksekusi nyata.
- Qwen menghasilkan JSON valid 100% (berkat structured output), tetapi konsistensi struktur combined dan kepatuhan pada field null masih lemah. Penurunan pada kalimat informal (66,7% intent) **berlawanan** dengan H2, tetapi belum dapat disimpulkan karena alasan validitas di atas.
- Latency NLU Qwen di laptop ±0,8 s.

## Lanjutan: skema v2 (disetujui peneliti 11 Nov 2026)
Skema v2 mengunci struktur per intent: field yang tidak relevan wajib null, dan `steps` hanya ada pada `combined_command` (≥ 2 langkah). Field utama tetap boleh null supaya model tidak dipaksa mengarang. Prompt tidak diubah (tetap v1), jadi efeknya murni dari skema. Ke-336 label (pilot + data latih) valid terhadap v2.

| Qwen2.5 (prompt v1) | Intent Accuracy | Exact Match | F1 weighted | t_nlu (s), n=36 | Sumber |
|---|---|---|---|---|---|
| Skema v1 | 80,56% | 63,89% | 0,7931 | 0,786 ± 0,387 | `results/summary_MSI_20261111_225631.md` |
| **Skema v2** | 80,56% | **69,44%** | 0,7931 | **0,678 ± 0,239** | `results/summary_MSI_20261111_230143.md` |

Per formalitas v2 (intent/EM): formal 83,3/75,0 · semi-formal 91,7/75,0 · informal 66,7/58,3.

- Kesalahan struktur (P23, P28, P35, field liar) hilang, dan latency turun karena token keluaran lebih sedikit.
- **Perintah gabungan masih gagal** (P25, P26, P29, P30). Dengan grammar yang terkunci, model memilih intent tindakan pertama di token awal, sehingga tidak bisa menulis `steps` lagi. Ini keterbatasan model 1,5B dalam merencanakan struktur sebelum menulis.
- Mulai sekarang set pilot berfungsi sebagai **set pengembangan** (*development set*): boleh dipakai untuk memperbaiki skema/prompt. Pengujian hipotesis hanya dilakukan pada data responden (F9) yang tidak pernah dipakai untuk pengembangan.

## Kalimat logbook
> Melakukan uji pendahuluan teks pada 36 kalimat pilot untuk tiga metode NLU; Qwen2.5 mencapai intent accuracy 80,56% dan exact match 63,89% dengan JSON valid 100% (latency 0,786 ± 0,387 s di laptop), sedangkan rule-based dan IndoBERT 100% pada set pilot yang disusun dengan kosakata yang sama sehingga belum dapat dipakai untuk menguji hipotesis.
