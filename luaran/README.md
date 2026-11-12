# Luaran

| Berkas | Isi |
|---|---|
| `buat_laporan_akhir.js` | Pembuat draf Laporan Akhir (.docx, format Buku Pedoman Asistensi Hibah LPPM UTM). Semua angka disalin dari `results/` (daftar di Lampiran 5 laporan). |

Menjalankan (Node.js, pustaka `docx` 9.5.1 dipasang di luar env conda):
```
npm install docx@9.5.1
node luaran/buat_laporan_akhir.js Laporan_Akhir_MBKM_Asad_Bahauddin_Ahmad_DRAF.docx
```
File .docx hasil tidak di-push (aturan `.gitignore`: dokumen administrasi). `[ISI ...]` (disorot kuning) = bagian yang diisi peneliti.
Setelah dibuka di Word: klik kanan Daftar Isi → Update Field.
