// Berkas unggahan e-HKI UTM, jenis Karya Lainnya / Program Komputer (Panduan Hak Cipta e-HKI UTM, 3.2.11):
//   HKI/Contoh_Ciptaan_Kode_Sumber.docx  -> source code lengkap (PDF dibuat lewat Word)
//   HKI/Bukti_Publikasi.docx             -> tangkapan layar setiap bagian program + keterangan + pseudocode (PDF lewat Word)
//   node luaran/buat_berkas_hki.js <daftar_file.txt>
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, ImageRun, AlignmentType, PageBreak, Footer, PageNumber } = require("docx");
const ROOT = path.join(__dirname, "..");
const OUT = path.join(ROOT, "HKI");
fs.mkdirSync(OUT, { recursive: true });
const JUDUL = "Program Pemahaman Perintah Suara Robot Berbahasa Indonesia secara Offline Berbasis Whisper dan Qwen2.5";
const REPO = "https://github.com/asadbahauddin/qwen25-indonesian-voice-command-intent";
const F = "Times New Roman";
const T = (t, o = {}) => new TextRun({ text: t, font: o.font || F, size: o.size || 22, bold: o.bold, italics: o.italics });
const P = (parts, o = {}) => new Paragraph({ alignment: o.align || AlignmentType.LEFT, spacing: { after: o.after ?? 80 },
  indent: o.indent, keepNext: o.keepNext, children: Array.isArray(parts) ? parts : [T(parts, o)] });
const info = () => [
  P([T("Judul : ", { bold: true }), T(JUDUL)]), P([T("Jenis Karya : ", { bold: true }), T("Karya Lainnya")]),
  P([T("Subjenis : ", { bold: true }), T("Program Komputer")]), P([T("Pencipta : ", { bold: true }), T("As'ad Bahauddin Ahmad; Vivi Tri Widyaningrum")]),
  P([T("Link publikasi / source code : ", { bold: true }), T(REPO)], { after: 200 }),
];
const footer = { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: F, size: 18 })] })] }) };
const page = { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } };

// ---------- 1. kode sumber ----------
const files = fs.readFileSync(process.argv[2], "utf-8").split(/\r?\n/).filter((f) => f && !f.endsWith(".json"));
const kode = [P(T("CONTOH CIPTAAN: KODE SUMBER LENGKAP", { bold: true, size: 26 }), { align: AlignmentType.CENTER, after: 200 }), ...info(),
  P(`Daftar berkas (${files.length}): ` + files.join(", "), { size: 18, after: 200 }),
  P("Berkas data uji (*.json) dan berkas lain disertakan pada arsip ZIP; dokumen ini memuat seluruh kode program.", { size: 18, italics: true })];
for (const f of files) {
  const lines = fs.readFileSync(path.join(ROOT, f), "utf-8").replace(/\t/g, "    ").split(/\r?\n/);
  kode.push(new Paragraph({ children: [new PageBreak()] }), P(T(`${f}  (${lines.length} baris)`, { bold: true, size: 22 }), { after: 120 }));
  lines.forEach((l, i) => kode.push(new Paragraph({ spacing: { after: 0, line: 220 }, children: [
    new TextRun({ text: String(i + 1).padStart(4, " ") + "  ", font: "Consolas", size: 14, color: "888888" }),
    new TextRun({ text: l || " ", font: "Consolas", size: 15 })] })));
}

// ---------- 2. bukti publikasi ----------
const TK = path.join(__dirname, "tangkapan");
const fig = (file, wPx, ket) => {
  const buf = fs.readFileSync(path.join(TK, file));
  const h = Math.round(wPx * buf.readUInt32BE(20) / buf.readUInt32BE(16));
  return [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: wPx, height: h }, altText: { title: ket, description: ket, name: file } })] }),
  P(ket, { align: AlignmentType.JUSTIFIED, after: 200, size: 20 })];
};
const PSEUDO = [
  ["ALGORITMA UTAMA: Pemahaman perintah suara robot", true],
  ["1. Mulai. Baca berkas konfigurasi config.yaml (parameter audio, VAD, Whisper, dan metode NLU).", false],
  ["2. Muat model satu kali: Silero VAD (ONNX), Whisper base (faster-whisper), dan metode NLU yang dipilih pengguna (Qwen2.5 melalui Ollama, rule-based, atau IndoBERT). Jalankan pemanasan agar waktu proses pertama tidak terlalu lambat.", false],
  ["3. Buka mikrofon pada sample rate asli perangkat, gabungkan kanal menjadi mono, lalu ubah sample rate menjadi 16 kHz.", false],
  ["4. Selama program berjalan, ulangi langkah berikut:", false],
  ["   a. Ambil potongan audio terbaru dan bagi menjadi frame 512 sampel (32 milidetik).", false],
  ["   b. Hitung peluang ucapan setiap frame dengan VAD.", false],
  ["   c. Jika sedang diam dan peluang ≥ 0,5, tandai awal ujaran dan sertakan 300 milidetik audio sebelumnya (pre-roll) agar awal kata tidak terpotong.", false],
  ["   d. Jika sedang dalam ujaran dan peluang < 0,35 selama 1,2 detik berturut-turut, tandai akhir ujaran dan buang sisa diam.", false],
  ["   e. Ubah audio ujaran menjadi teks dengan Whisper base (bahasa Indonesia, petunjuk awal berisi nama ruangan, benda, orang, dan dokumen di laboratorium).", false],
  ["   f. Untuk setiap metode NLU yang aktif, ubah teks menjadi perintah robot berformat JSON berisi intent, room, object, person, document, dan steps; samakan penulisan entitas dengan nama baku di kamus; periksa kesesuaian dengan skema.", false],
  ["   g. Tampilkan transkrip, JSON, dan waktu setiap tahap (VAD, Whisper, NLU, total) di layar, lalu simpan ke berkas log CSV.", false],
  ["5. Jika pengguna mengetik perintah (/metode, /mode, /whisper, /beam, /perangkat, /file, /stat, /simpan, /bantuan), ubah pengaturan atau tampilkan informasi tanpa memulai ulang program. Perintah /keluar menghentikan program.", false],
  ["SUB-ALGORITMA NLU: Qwen2.5", true],
  ["1. Susun pesan berisi instruksi sistem berbahasa Indonesia (dengan enam contoh) dan kalimat perintah.", false],
  ["2. Kirim ke server Ollama lokal dengan batasan keluaran berupa skema JSON, suhu 0, dan seed tetap agar hasil konsisten.", false],
  ["3. Model menyusun jawaban kata demi kata, hanya dari pilihan yang tetap membentuk JSON yang sah; baca JSON, samakan nama entitas, dan periksa skema.", false],
  ["SUB-ALGORITMA NLU: Rule-based", true],
  ["1. Pecah kalimat menjadi beberapa klausa pada kata penghubung (lalu, kemudian, setelah itu, habis itu, terus, selanjutnya, dan sejenisnya).", false],
  ["2. Untuk setiap klausa, cari kata kunci tiap intent dan entitas dari kamus (alias terpanjang lebih dulu).", false],
  ["3. Jika terdapat dua klausa atau lebih yang bermakna, hasilnya combined_command dengan setiap klausa sebagai langkah; jika tidak, hasilnya intent klausa tersebut.", false],
  ["SUB-ALGORITMA NLU: IndoBERT", true],
  ["1. Pecah kalimat menjadi klausa seperti pada rule-based.", false],
  ["2. Klasifikasikan intent setiap klausa dengan model IndoBERT yang telah dilatih (kelas dengan peluang terbesar).", false],
  ["3. Ambil entitas dari kamus dan susun JSON; dua klausa atau lebih menjadi combined_command.", false],
  ["ALAT EVALUASI", true],
  ["1. Untuk setiap rekaman uji, jalankan ketiga metode pada teks acuan, rekaman utuh, dan segmen VAD, baik dengan GPU maupun hanya CPU.", false],
  ["2. Hitung Word Error Rate, akurasi intent, exact match, F1, confusion matrix, uji McNemar, dan waktu proses; simpan hasil ke folder results/.", false],
];
const bukti = [P(T("BUKTI PUBLIKASI PROGRAM KOMPUTER", { bold: true, size: 26 }), { align: AlignmentType.CENTER, after: 200 }), ...info(),
  P(T("A. Publikasi", { bold: true, size: 24 }), { keepNext: true }),
  P("Program dipublikasikan pertama kali melalui repositori GitHub publik pada 11 November 2026 dan dapat diakses di " + REPO + ".", { align: AlignmentType.JUSTIFIED }),
  ...fig("05_github_repo.png", 560, "Gambar 1. Halaman repositori GitHub publik: berisi kode program (src/), skrip pengujian (bench/), konfigurasi, model prompt, dan riwayat pengembangan."),
  new Paragraph({ children: [new PageBreak()] }),
  P(T("B. Tangkapan Layar Setiap Bagian Program", { bold: true, size: 24 }), { keepNext: true }),
  ...fig("01_mulai_bantuan.png", 600, "Gambar 2. Halaman awal program (antarmuka baris perintah). Berfungsi sebagai halaman utama yang menampilkan status program (metode NLU, mode masukan, model Whisper, beam, perangkat, RAM tersedia) dan daftar perintah (/bantuan) untuk mengganti pengaturan tanpa memulai ulang program."),
  ...fig("02_mode_teks.png", 600, "Gambar 3. Mode teks. Kalimat perintah yang diketik diproses oleh tiga metode NLU (Qwen2.5, rule-based, IndoBERT). Setiap metode menampilkan JSON perintah robot, dan tabel di bawahnya menampilkan waktu proses tiap tahap serta statistik Qwen2.5 (token per detik)."),
  ...fig("03_file_audio_gpu.png", 520, "Gambar 4. Pemrosesan masukan suara. Rekaman perintah majemuk melewati deteksi aktivitas suara dan transkripsi Whisper (kotak Transkrip Whisper), lalu diubah oleh ketiga metode menjadi JSON; rule-based dan IndoBERT memecahnya menjadi dua langkah (steps)."),
  ...fig("04_cpu_stat.png", 470, "Gambar 5. Penggantian perangkat proses dari GPU ke CPU tanpa memulai ulang program (/perangkat cpu), pemrosesan ulang audio yang sama, dan statistik sesi (/stat) berupa rata-rata ± simpangan baku waktu proses setiap metode."),
  new Paragraph({ children: [new PageBreak()] }),
  P(T("C. Pseudocode (Penjelasan Alur Program)", { bold: true, size: 24 }), { keepNext: true, after: 120 }),
  ...PSEUDO.map(([t, h]) => P(h ? T(t, { bold: true }) : T(t), { align: AlignmentType.JUSTIFIED, keepNext: h, after: h ? 60 : 40,
    indent: !h && t.startsWith("   ") ? { left: 567 } : undefined })),
];
const mk = (children, name) => Packer.toBuffer(new Document({ sections: [{ properties: { page }, footers: footer, children }] }))
  .then((b) => { fs.writeFileSync(path.join(OUT, name), b); console.log("ditulis", name, b.length); });
mk(kode, "Contoh_Ciptaan_Kode_Sumber.docx").then(() => mk(bukti, "Bukti_Publikasi.docx"));
