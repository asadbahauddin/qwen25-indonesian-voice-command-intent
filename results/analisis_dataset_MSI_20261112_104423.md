# F9 analisis lanjutan — dataset (MSI, 20261112_104423)

Sumber per item: `eval_item_dataset_MSI_20261112_095743.csv`.

## 1. F1 per intent (laptop GPU)

Kelas seimbang (27 item per intent), sehingga F1 weighted = F1 macro.

**Masukan teks** — F1 (precision / recall):

| Intent | Qwen2.5 1.5B | Rule-based | IndoBERT |
|---|---|---|---|
| navigate_room | 0.68 (0.52 / 1.00) | 0.93 (0.90 / 0.96) | 0.96 (0.93 / 1.00) |
| navigate_object | 0.86 (0.75 / 1.00) | 0.91 (0.87 / 0.96) | 0.96 (0.93 / 1.00) |
| find_person | 0.93 (0.87 / 1.00) | 0.85 (0.78 / 0.93) | 1.00 (1.00 / 1.00) |
| deliver_document | 0.96 (0.93 / 1.00) | 0.88 (0.83 / 0.93) | 0.96 (0.93 / 1.00) |
| combined_command | 0.07 (1.00 / 0.04) | 0.54 (1.00 / 0.37) | 0.88 (1.00 / 0.78) |
| general_command | 0.65 (1.00 / 0.48) | 0.93 (0.87 / 1.00) | 1.00 (1.00 / 1.00) |

**Masukan vad** — F1 (precision / recall):

| Intent | Qwen2.5 1.5B | Rule-based | IndoBERT |
|---|---|---|---|
| navigate_room | 0.67 (0.51 / 0.96) | 0.55 (0.71 / 0.44) | 0.77 (0.90 / 0.67) |
| navigate_object | 0.64 (0.47 / 1.00) | 0.78 (0.86 / 0.70) | 0.78 (0.65 / 0.96) |
| find_person | 0.71 (0.89 / 0.59) | 0.64 (0.54 / 0.78) | 0.87 (0.88 / 0.85) |
| deliver_document | 0.90 (0.96 / 0.85) | 0.78 (0.83 / 0.74) | 0.96 (0.96 / 0.96) |
| combined_command | 0.13 (0.67 / 0.07) | 0.41 (1.00 / 0.26) | 0.92 (1.00 / 0.85) |
| general_command | 0.46 (1.00 / 0.30) | 0.68 (0.51 / 1.00) | 0.75 (0.77 / 0.74) |

## 2. Uji McNemar eksak (dua sisi), item yang sama

b = A benar & B salah, c = A salah & B benar; p < 0,05 = beda bermakna.

| Platform | Masukan | Metrik | A vs B | b | c | p |
|---|---|---|---|---|---|---|
| gpu | teks | intent | Qwen2.5 1.5B vs Rule-based | 6 | 23 | 0.0023 * |
| gpu | teks | intent | Qwen2.5 1.5B vs IndoBERT | 0 | 34 | 0.0000 * |
| gpu | teks | intent | Rule-based vs IndoBERT | 1 | 18 | 0.0001 * |
| gpu | teks | EM | Qwen2.5 1.5B vs Rule-based | 2 | 34 | 0.0000 * |
| gpu | teks | EM | Qwen2.5 1.5B vs IndoBERT | 2 | 34 | 0.0000 * |
| gpu | teks | EM | Rule-based vs IndoBERT | 1 | 1 | 1.0000 |
| gpu | utuh | intent | Qwen2.5 1.5B vs Rule-based | 32 | 40 | 0.4096 |
| gpu | utuh | intent | Qwen2.5 1.5B vs IndoBERT | 9 | 47 | 0.0000 * |
| gpu | utuh | intent | Rule-based vs IndoBERT | 11 | 41 | 0.0000 * |
| gpu | utuh | EM | Qwen2.5 1.5B vs Rule-based | 20 | 46 | 0.0019 * |
| gpu | utuh | EM | Qwen2.5 1.5B vs IndoBERT | 20 | 36 | 0.0440 * |
| gpu | utuh | EM | Rule-based vs IndoBERT | 11 | 1 | 0.0063 * |
| gpu | vad | intent | Qwen2.5 1.5B vs Rule-based | 30 | 34 | 0.7080 |
| gpu | vad | intent | Qwen2.5 1.5B vs IndoBERT | 11 | 45 | 0.0000 * |
| gpu | vad | intent | Rule-based vs IndoBERT | 9 | 39 | 0.0000 * |
| gpu | vad | EM | Qwen2.5 1.5B vs Rule-based | 15 | 40 | 0.0010 * |
| gpu | vad | EM | Qwen2.5 1.5B vs IndoBERT | 15 | 32 | 0.0186 * |
| gpu | vad | EM | Rule-based vs IndoBERT | 9 | 1 | 0.0215 * |
| cpu | teks | intent | Qwen2.5 1.5B vs Rule-based | 6 | 18 | 0.0227 * |
| cpu | teks | intent | Qwen2.5 1.5B vs IndoBERT | 0 | 29 | 0.0000 * |
| cpu | teks | intent | Rule-based vs IndoBERT | 1 | 18 | 0.0001 * |
| cpu | teks | EM | Qwen2.5 1.5B vs Rule-based | 3 | 26 | 0.0000 * |
| cpu | teks | EM | Qwen2.5 1.5B vs IndoBERT | 3 | 26 | 0.0000 * |
| cpu | teks | EM | Rule-based vs IndoBERT | 1 | 1 | 1.0000 |
| cpu | utuh | intent | Qwen2.5 1.5B vs Rule-based | 29 | 37 | 0.3891 |
| cpu | utuh | intent | Qwen2.5 1.5B vs IndoBERT | 10 | 45 | 0.0000 * |
| cpu | utuh | intent | Rule-based vs IndoBERT | 11 | 38 | 0.0001 * |
| cpu | utuh | EM | Qwen2.5 1.5B vs Rule-based | 18 | 40 | 0.0054 * |
| cpu | utuh | EM | Qwen2.5 1.5B vs IndoBERT | 19 | 30 | 0.1524 |
| cpu | utuh | EM | Rule-based vs IndoBERT | 11 | 0 | 0.0010 * |
| cpu | vad | intent | Qwen2.5 1.5B vs Rule-based | 29 | 35 | 0.5323 |
| cpu | vad | intent | Qwen2.5 1.5B vs IndoBERT | 9 | 39 | 0.0000 * |
| cpu | vad | intent | Rule-based vs IndoBERT | 13 | 37 | 0.0009 * |
| cpu | vad | EM | Qwen2.5 1.5B vs Rule-based | 19 | 38 | 0.0163 * |
| cpu | vad | EM | Qwen2.5 1.5B vs IndoBERT | 19 | 28 | 0.2430 |
| cpu | vad | EM | Rule-based vs IndoBERT | 11 | 1 | 0.0063 * |

Qwen laptop GPU vs laptop CPU (item yang sama):

- teks: keluaran JSON berbeda pada 13/162 item; EM GPU-benar/CPU-salah 0, sebaliknya 9, p = 0.0039
- utuh: keluaran JSON berbeda pada 36/162 item; EM GPU-benar/CPU-salah 3, sebaliknya 8, p = 0.2266
- vad: keluaran JSON berbeda pada 43/162 item; EM GPU-benar/CPU-salah 4, sebaliknya 10, p = 0.1796

## 3. Jenis kesalahan (laptop GPU)

Kolom = item salah EM; dipecah: intent salah, atau intent benar tetapi field tertentu salah (satu item bisa >1 field).

| Metode | Masukan | Salah EM | intent | room | object | person | document | steps* | JSON tak valid |
|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5 1.5B | teks | 56 | 40 | 9 | 0 | 11 | 2 | 1 | 0 |
| Rule-based | teks | 24 | 23 | 0 | 0 | 0 | 0 | 1 | 0 |
| IndoBERT | teks | 24 | 6 | 1 | 1 | 2 | 1 | 13 | 0 |
| Qwen2.5 1.5B | utuh | 89 | 62 | 12 | 3 | 12 | 3 | 2 | 1 |
| Rule-based | utuh | 63 | 55 | 5 | 0 | 4 | 0 | 2 | 0 |
| IndoBERT | utuh | 73 | 25 | 12 | 7 | 10 | 5 | 18 | 0 |
| Qwen2.5 1.5B | vad | 88 | 60 | 13 | 3 | 14 | 3 | 2 | 0 |
| Rule-based | vad | 63 | 56 | 4 | 0 | 3 | 0 | 2 | 0 |
| IndoBERT | vad | 71 | 26 | 12 | 7 | 9 | 4 | 19 | 0 |

*steps = combined_command: jumlah langkah / intent langkah / entity langkah salah.

- Pasangan intent tertukar terbanyak, Qwen2.5 1.5B (teks): general_command→navigate_room (13), combined_command→navigate_room (12), combined_command→navigate_object (8), combined_command→find_person (4)
- Pasangan intent tertukar terbanyak, Rule-based (teks): combined_command→find_person (6), combined_command→deliver_document (5), combined_command→navigate_object (4), combined_command→navigate_room (2)
- Pasangan intent tertukar terbanyak, IndoBERT (teks): combined_command→navigate_room (2), combined_command→deliver_document (2), combined_command→navigate_object (2)

## 4. Dampak galat ASR (laptop GPU): EM benar pada teks → salah pada transkrip VAD

| Metode | Benar di teks | ... tetap benar di vad | ... jadi salah | salah di teks tapi benar di vad |
|---|---|---|---|---|
| Qwen2.5 1.5B | 106 | 69 | 37 | 5 |
| Rule-based | 138 | 97 | 41 | 2 |
| IndoBERT | 138 | 89 | 49 | 2 |

## 5. Pencilan waktu respons > 15 s (masukan vad)

- RAM tersedia saat uji gpu: min 0.41 GB, median 0.89 GB
- cpu/Qwen2.5 1.5B: 4/162 ujaran — R02_S51 26.0 s (ASR 5.2, NLU 19.7, RAM 0.41 GB); R01_S36 19.3 s (ASR 9.8, NLU 8.3, RAM 0.44 GB); R02_S29 18.1 s (ASR 7.7, NLU 9.2, RAM 0.24 GB); R01_S48 16.1 s (ASR 8.4, NLU 6.5, RAM 0.33 GB)
- RAM tersedia saat uji cpu: min 0.20 GB, median 0.77 GB
