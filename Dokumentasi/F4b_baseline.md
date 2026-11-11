# F4b — Baseline Rule-based dan IndoBERT (antarmuka sama dengan Qwen)

**Tanggal:** 11 November 2026 · **Perangkat:** laptop MSI (RTX 2050)
**Bukti:** [F4b_bukti_baseline.txt](F4b_bukti_baseline.txt) (salinan `results/f4b_uji_cepat_MSI_*.txt`), `results/indobert_train_MSI_20261111_225006.json`
**File:** `src/nlu/rule.py`, `src/nlu/indobert.py`, `src/nlu/entities.py`, `config/keywords_id.yaml` (v1), `bench/buat_data_latih.py`, `bench/latih_indobert.py`, `data/indobert_train.jsonl`

## 1. Kamus entity bersama (`src/nlu/entities.py`)
- Entity diambil dari `config/domain_id.yaml`, yaitu kosakata yang sama dengan yang dipakai di prompt Qwen.
- Pencocokan memakai **alias terpanjang lebih dulu, tanpa tumpang tindih**. Contoh: "ruangan Pak Umam" dibaca sebagai *room*, bukan *person*; "ruang asisten" dibaca sebagai *room*, bukan *person* "asisten".
- Kalimat dipecah per klausa pada kata penghubung (lalu, kemudian, habis itu, terus, ...). Kata ganti "beliau/dia" diisi orang dari klausa sebelumnya.

## 2. Rule-based (baseline bawah)
Urutan aturan untuk tiap klausa:
1. Ada dokumen → `deliver_document` (tujuan: orang bila ada, selain itu ruangan).
2. Ada orang + kata "cari/temukan/panggil/di mana" → `find_person`.
3. Ada ruangan → `navigate_room`.
4. Ada benda → `navigate_object`.
5. Ada orang saja → `find_person`.
6. Selain itu → `general_command`.

Jika ada ≥ 2 klausa tindakan, hasilnya `combined_command` dengan `steps`.

Kamus intent ada di `config/keywords_id.yaml`. **Kamus tidak disetel memakai kalimat pilot**, supaya pilot tetap menjadi data uji yang adil.

## 3. Data latih IndoBERT (`data/indobert_train.jsonl`)
| Item | Nilai |
|---|---|
| Jumlah | 300 kalimat = 6 intent × 50 (formal 17 / semi-formal 17 / informal 16 per intent) |
| Sumber | Sintetis berbasis templat (`bench/buat_data_latih.py`, seed 42, bisa dibuat ulang persis) |
| Entity | Bentuk ucapan memakai alias (mis. "robot arm", "trainer RL", "laprak"); label memakai nama kanonik |
| Anti-kebocoran | Kalimat yang sama dengan 36 kalimat pilot atau 6 contoh di prompt Qwen dibuang, lalu diverifikasi ulang: **0 kebocoran** |
| Duplikat dibuang | 29 |

Keterbatasan: data latih dan set pilot disusun oleh pihak yang sama (gaya bahasanya mirip). Dataset responden (F9) menjadi uji yang lebih independen.

## 4. IndoBERT fine-tuning (`bench/latih_indobert.py`)
| Parameter | Nilai |
|---|---|
| Model dasar | `indobenchmark/indobert-base-p1` (salinan lokal `models/indobert-base-p1`, 474,7 MB) |
| Tugas | Klasifikasi intent (6 kelas). Entity memakai kamus yang sama dengan rule-based. |
| Split | train 255 / val 45 (stratified, seed 42). Val hanya untuk memilih epoch, **bukan data uji**. |
| Hyperparameter | max_len 64, batch 16, lr 3e-5, weight decay 0,01, warmup 10%, 8 epoch, AdamW, fp16 (CUDA) |
| Perangkat | RTX 2050, total 422,6 s |
| Hasil val | Akurasi 1,0000 sejak epoch 1, F1 macro 1,0000; epoch terbaik = 8 (loss val terendah 0,0045) |

**Interpretasi jujur:** akurasi val 100% hanya menunjukkan model sudah mempelajari pola templat, karena val berasal dari templat yang sama. Angka ini **bukan** hasil penelitian. Kemampuan sebenarnya diukur pada set pilot (F6) dan dataset responden (F9).

Untuk `combined_command`, IndoBERT memprediksi intent keseluruhan kalimat. Kalimat lalu dipecah per klausa, dan tiap klausa diklasifikasi ulang oleh IndoBERT (dibatasi ke 5 intent non-combined).

## 5. Uji cepat (2 kalimat yang sama dengan F4, bukan pilot)
| Kalimat | Rule-based | IndoBERT |
|---|---|---|
| "Tolong antarkan surat izin ke Pak Umam" | ✅ deliver_document (pak umam, surat izin) | ✅ sama, prob 0,995 |
| "Robot, ke trainer PLC dulu, habis itu cari Bu Vivi ya" | ✅ combined: trainer plc → bu vivi | ✅ sama, prob 0,995 |

## 6. Paket baru
`transformers 5.22.2`, `scikit-learn 1.9.1`, `jiwer 4.0.0`, `rich 15.0.0`. Sebelum dipasang sudah dicek dengan dry-run (tidak ada konflik, torch tidak berubah), dan `pip check` bersih. `environment.yml` dan `requirements-lock-laptop.txt` sudah diperbarui.

## Catatan
- Model hasil fine-tuning (`models/indobert_intent`, ±498 MB) **tidak di-push** ke GitHub karena terlalu besar dan di-ignore. Model bisa dibuat ulang dengan `python bench/latih_indobert.py`, atau disalin manual ke RPi 5.
- Training dan penyimpanan model terasa lambat (±30 s/epoch, simpan 110 s). Dugaan: mode daya laptop atau antivirus. Hasil training tidak terpengaruh.

## Cara menjalankan
```powershell
$PY = "C:\Users\indie\.conda\envs\mbkm-nlu\python.exe"
& $PY bench\buat_data_latih.py         # buat ulang data latih
& $PY bench\latih_indobert.py          # fine-tuning IndoBERT
& $PY -m src.nlu.rule "kalimat"        # uji rule-based
& $PY -m src.nlu.indobert "kalimat"    # uji IndoBERT
```

## Kalimat logbook
> Membangun dua baseline dengan antarmuka yang sama dengan Qwen: rule-based keyword matching (kamus v1) dan IndoBERT-base-p1 yang di-fine-tune pada 300 kalimat sintetis (50 per intent, tanpa kebocoran ke set pilot); keduanya memakai kamus entity bersama dan lolos uji cepat termasuk perintah gabungan.
