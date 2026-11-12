# Luaran

| Berkas | Isi |
|---|---|
| `gambar/*.png` | Grafik 300 dpi (versi `_id` koma desimal, `_en` untuk artikel) dari `bench/grafik_f10.py`; sumber JSON di `gambar/sumber.txt` |
| `buat_laporan_akhir.js` | Pembuat draf Laporan Akhir (.docx, format Buku Pedoman Asistensi Hibah LPPM UTM). Semua angka disalin dari `results/` (daftar di Lampiran 5 laporan). |

Menjalankan (Node.js, pustaka `docx` 9.5.1 dipasang di luar env conda):
```
npm install docx@9.5.1
node luaran/buat_laporan_akhir.js Laporan_Akhir_MBKM_Asad_Bahauddin_Ahmad_DRAF.docx
```
File .docx hasil tidak di-push (aturan `.gitignore`: dokumen administrasi). `[ISI ...]` (disorot kuning) = bagian yang diisi peneliti.
Sesudah dibuat, hapus entri folder di arsip (Word bisa menolaknya lewat layanan cloud):
```
python -c "import zipfile,shutil;s='Laporan_Akhir_MBKM_Asad_Bahauddin_Ahmad_DRAF.docx';t=s+'.tmp';zi=zipfile.ZipFile(s);zo=zipfile.ZipFile(t,'w',zipfile.ZIP_DEFLATED);[zo.writestr(i,zi.read(i.filename)) for i in zi.infolist() if not i.filename.endswith('/')];zo.close();zi.close();shutil.move(t,s)"
```
Setelah dibuka di Word: klik kanan Daftar Isi → Update Field.
| `buat_artikel_joti.py` | Draf artikel JoTI: mengisi `Template JoTI Baru 2025.docx` (header, kotak info, logo, gaya dipertahankan). Bahasa Indonesia, abstrak Inggris, IEEE, grafik `_id`. `python luaran/buat_artikel_joti.py "Template JoTI Baru 2025.docx" Artikel_JoTI_DRAF.docx` |
| `tangkapan_cli.py` → `tangkapan/*.png` | Tangkapan layar CLI asli (src/cli.py dijalankan dengan masukan pilot, tampilan rich direkam lalu dirender Edge headless); keterangan di `tangkapan/keterangan.txt` |
