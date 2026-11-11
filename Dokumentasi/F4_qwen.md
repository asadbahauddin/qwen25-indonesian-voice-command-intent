# F4 — NLU Qwen2.5 via Ollama (JSON schema + prompt engineering)

**Tanggal:** 11 November 2026 · **Perangkat:** laptop MSI (RTX 2050), Ollama 0.30.6, `qwen2.5:1.5b` (Q4_K_M, konteks 32k)
**Bukti:** [F4_bukti_qwen.txt](F4_bukti_qwen.txt) (salinan `results/qwen_uji_cepat_MSI_*.txt`)
**File:** `src/nlu/base.py`, `src/nlu/qwen.py`, `prompts/system_id.txt` (v1), `config.yaml` (bagian `nlu`)

## Rancangan
| Komponen | Isi |
|---|---|
| Antarmuka bersama (`base.py`) | `predict(text) -> (command, info)` untuk ketiga metode. Berisi skema JSON (`COMMAND_SCHEMA`), validasi `jsonschema`, dan normalisasi entity. |
| Skema perintah | `intent` (6 pilihan), `room`/`object`/`person`/`document` (string atau null), `steps` (null atau array sub-perintah). Disetujui peneliti 11 Nov 2026. |
| `combined_command` | Field tingkat atas null. Tindakan ditulis berurutan di `steps`, dan tiap langkah memakai intent selain combined. |
| Normalisasi entity | Huruf kecil, tanda baca dibuang, alias dipetakan ke nama kanonik dari `config/domain_id.yaml` (mis. "alat CNC" → "mesin cnc"). Diterapkan **sama** untuk semua metode. |
| Pemanggilan model | HTTP `POST /api/chat` dengan `requests`. Paket `ollama` tidak dipakai agar tidak menambah dependensi; caranya sama di RPi 5. |
| Structured output | `format` = JSON schema, sehingga Ollama membatasi token yang dihasilkan (grammar-constrained) dan model **tidak bisa** mengeluarkan JSON di luar skema. |
| Parameter | `temperature 0`, `seed 42` (deterministik untuk evaluasi), `num_ctx 2048`, `num_predict 256`, `keep_alive 30m`. Semua ada di `config.yaml`. |
| System prompt v1 | Definisi 6 intent, 5 aturan, daftar nama baku (diisi otomatis dari `domain_id.yaml`), dan 6 contoh (*few-shot*). ±922 token. SHA-256 (12 karakter awal): `114d424e5d61`. |

## Pencegahan kebocoran data
- 6 contoh di prompt dicek otomatis: **tidak ada** yang sama dengan 36 kalimat pilot.
- Contoh di prompt dianggap "data latih" Qwen, sehingga **tidak boleh** dipakai di set pilot maupun dataset responden.
- Ke-36 label pilot lolos validasi skema, dan tidak berubah setelah normalisasi.

## Uji cepat (1 sampel per kalimat, bukan benchmark)
| Kalimat | JSON keluaran | Valid |
|---|---|---|
| "Tolong antarkan surat izin ke Pak Umam" | `deliver_document`, person `pak umam`, document `surat izin` | ✅ JSON + skema |
| "Robot, ke trainer PLC dulu, habis itu cari Bu Vivi ya" | `combined_command`, steps: `navigate_object` (trainer plc) → `find_person` (bu vivi) | ✅ JSON + skema |

Data waktu (satu kali eksekusi, hanya sebagai gambaran): t_nlu 1,39 s dan 2,07 s; ±78 token/s; prompt 922–927 token. Latency resmi akan diukur di F6 (n = 36) dan F9.

## Temuan dan catatan
1. Model berjalan penuh di GPU (VRAM 1054 MiB dari 4096 MiB).
2. Muat dingin (*cold load*) model ±6,5–9 s, sehingga `warmup()` dipanggil sebelum pengukuran latency.
3. `load_duration` masih 0,3–0,5 s per permintaan walaupun model sudah dimuat. Ini akan diselidiki di F6.
4. Prompt ±922 token cepat di GPU (prompt_eval ±0,05 s). Di RPi 5 (CPU) bisa beberapa detik; ini akan diukur di F7 bersama efek cache prompt Ollama.

## Cara menjalankan
```powershell
& "C:\Users\indie\.conda\envs\mbkm-nlu\python.exe" -m src.nlu.qwen "Tolong antarkan surat izin ke Pak Umam"
```

## Kalimat logbook
> Mengimplementasikan modul NLU Qwen2.5 1.5B (Q4_K_M) melalui Ollama dengan system prompt v1 dan keluaran dibatasi JSON schema, serta antarmuka `predict()` yang seragam untuk ketiga metode; uji cepat menghasilkan JSON valid dengan intent dan entity yang tepat, termasuk perintah gabungan.
