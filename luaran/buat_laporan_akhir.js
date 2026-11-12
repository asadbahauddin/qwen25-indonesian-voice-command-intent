// Draf Laporan Akhir MBKM (format Buku Pedoman Asistensi Hibah LPPM UTM, Lampiran 1, 6, 7)
// Semua angka berasal dari results/ (lihat Lampiran 5). [ISI ...] = diisi peneliti.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, AlignmentType, HeadingLevel,
  WidthType, BorderStyle, ShadingType, PageBreak, TableOfContents, Footer, PageNumber, LevelFormat,
  VerticalAlign, TabStopType, ImageRun,
} = require("docx");
const path = require("path");
const GBR = path.join(__dirname, "gambar");

const FONT = "Times New Roman";
const CM = 567; // dxa per cm
const PAGE_W = 11906, ML = 4 * CM, MR = 3 * CM; // A4, kiri 4, kanan 3
const TW = PAGE_W - ML - MR; // lebar isi

// ---------- helper ----------
function runs(text, o = {}) {
  text = text.replace(/`/g, "");
  // **tebal**, _miring_, [ISI ...] disorot kuning
  const out = [];
  const re = /(\*\*[^*]+\*\*|(?<![\w])_[^_]+?_(?![\w])|\[ISI[^\]]*\]|\[KEPUTUSAN[^\]]*\])/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, size: o.size || 24, bold: o.bold, italics: o.italics }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), font: FONT, size: o.size || 24, bold: true, italics: o.italics }));
    else if (t.startsWith("_")) out.push(new TextRun({ text: t.slice(1, -1), font: FONT, size: o.size || 24, italics: true, bold: o.bold }));
    else out.push(new TextRun({ text: t, font: FONT, size: o.size || 24, bold: true, highlight: "yellow" }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, size: o.size || 24, bold: o.bold, italics: o.italics }));
  return out;
}
const P = (text, o = {}) => new Paragraph({
  children: runs(text, o), alignment: o.align || AlignmentType.JUSTIFIED,
  indent: o.noIndent ? undefined : { firstLine: o.first === undefined ? 720 : o.first },
  spacing: { line: 240, after: o.after === undefined ? 120 : o.after, before: o.before || 0 }, keepNext: o.keepNext,
});
const C = (text, o = {}) => P(text, { ...o, align: AlignmentType.CENTER, noIndent: true });
const BAB = (no, judul) => [
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, spacing: { after: 0 },
    children: [new TextRun({ text: no, font: FONT, size: 24, bold: true }), new TextRun({ text: judul, font: FONT, size: 24, bold: true, break: 1 })] }),
  new Paragraph({ children: [], spacing: { after: 120 } }),
];
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT, size: 24, bold: true })], spacing: { before: 120, after: 80 }, keepNext: true });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: t, font: FONT, size: 24, bold: true })], spacing: { before: 80, after: 60 }, keepNext: true });
const NUM = (text, ref = "angka", level = 0) => new Paragraph({ numbering: { reference: ref, level }, children: runs(text), alignment: AlignmentType.JUSTIFIED, spacing: { line: 240, after: 60 } });
const BUL = (text) => NUM(text, "titik");
const CAP = (t) => new Paragraph({ children: [new TextRun({ text: t, font: FONT, size: 24, bold: true })], alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true });
const NOTE = (t) => P(t, { noIndent: true, size: 20, after: 160 });

const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };
function T(header, rows, widthsCm, o = {}) {
  const tot = widthsCm.reduce((a, b) => a + b, 0);
  const w = widthsCm.map((x) => Math.round((x / tot) * TW));
  w[w.length - 1] += TW - w.reduce((a, b) => a + b, 0);
  const sz = o.size || 20;
  const cell = (txt, i, head) => new TableCell({
    borders, width: { size: w[i], type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: head ? { fill: "D9D9D9", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: String(txt).split("\n").map((line) => new Paragraph({ children: runs(line, { size: sz, bold: head }),
      alignment: head || (i > 0 && o.centerCols && o.centerCols.includes(i)) ? AlignmentType.CENTER : AlignmentType.LEFT })),
  });
  return new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: w,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => cell(c, i, false)) }))] });
}
const GAP = () => new Paragraph({ children: [], spacing: { after: 120 } });
// Gambar: judul di BAWAH gambar (Lampiran 1 pedoman). Ukuran dalam piksel (96 dpi): lebar isi ±567 px.
const FIG = (file, w, h, caption) => [
  new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
    children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(GBR, file)), transformation: { width: w, height: h },
      altText: { title: caption, description: caption, name: file } })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: runs(caption, { size: 22 }) }),
];

// ---------- isi ----------
const JUDUL = "EVALUASI LARGE LANGUAGE MODEL QWEN2.5 UNTUK EKSTRAKSI INTENT PERINTAH KALIMAT BEBAS BAHASA INDONESIA PADA ROBOT";
const children = [];

// SAMPUL (Lampiran 6)
children.push(
  new Paragraph({ children: [], spacing: { after: 600 } }),
  C("**LAPORAN AKHIR**", { size: 28, after: 0 }),
  C("Asistensi Hibah Penelitian", { size: 24, after: 480 }),
  C(`**${JUDUL}**`, { size: 24, after: 600 }),
  C("[ISI: logo Universitas Trunojoyo Madura 4 × 4 cm]", { after: 600 }),
  C("Disusun oleh:", { after: 60 }),
  C("As'ad Bahauddin Ahmad          NIM. 230491100034", { after: 240 }),
  C("Dibimbing oleh:", { after: 60 }),
  C("Ir. Vivi Tri Widyaningrum, S.Kom., M.T.          NIDN. 198308072008122001", { after: 900 }),
  C("**LEMBAGA PENELITIAN DAN PENGABDIAN KEPADA MASYARAKAT**", { after: 0 }),
  C("**UNIVERSITAS TRUNODJOYO MADURA**", { after: 0 }),
  C("**BANGKALAN DESEMBER 2026**", { after: 0 }),
);

// PENGESAHAN (Lampiran 7)
const idRow = (a, b) => new TableRow({ children: [
  new TableCell({ width: { size: 3200, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }, children: [new Paragraph({ children: runs(a) })] }),
  new TableCell({ width: { size: 300, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }, children: [new Paragraph({ children: runs(":") })] }),
  new TableCell({ width: { size: TW - 3500, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }, children: [new Paragraph({ children: runs(b) })] }),
] });
children.push(
  new Paragraph({ children: [new PageBreak()] }),
  C("**PENGESAHAN**", { after: 0 }), C("**IDENTITAS LAPORAN AKHIR**", { after: 0 }), C("**Asistensi Hibah Penelitian**", { after: 360 }),
  new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: [3200, 300, TW - 3500], rows: [
    idRow("Judul Penelitian", "Evaluasi Large Language Model Qwen2.5 untuk Ekstraksi Intent Perintah Kalimat Bebas Bahasa Indonesia pada Robot"),
    idRow("Identitas Mahasiswa", ""), idRow("    a. Nama Lengkap", "As'ad Bahauddin Ahmad"), idRow("    b. NIM", "230491100034"),
    idRow("    c. Program Studi", "Teknik Mekatronika"), idRow("    d. Jurusan", "Teknik Elektro"), idRow("    e. Fakultas", "Teknik"),
    idRow("Dosen Pembimbing", ""), idRow("    a. Nama Lengkap", "Ir. Vivi Tri Widyaningrum, S.Kom., M.T."), idRow("    b. NIDN", "198308072008122001"),
    idRow("    c. Program Studi", "Teknik Mekatronika"), idRow("    d. Jurusan", "Teknik Elektro"), idRow("    e. Fakultas", "Teknik"),
  ] }),
  new Paragraph({ children: [], spacing: { after: 360 } }),
  P("Bangkalan, [ISI: tanggal] Desember 2026", { align: AlignmentType.RIGHT, noIndent: true }),
  new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: [TW / 2, TW / 2], rows: [new TableRow({ children: [
    new TableCell({ width: { size: TW / 2, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } },
      children: [P("Mengetahui,", { noIndent: true, after: 0 }), P("Dosen Pembimbing", { noIndent: true, after: 1100 }), P("**Ir. Vivi Tri Widyaningrum, S.Kom., M.T.**", { noIndent: true, after: 0, align: AlignmentType.LEFT }), P("NIDN. 198308072008122001", { noIndent: true })] }),
    new TableCell({ width: { size: TW / 2, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } },
      children: [P(" ", { noIndent: true, after: 0 }), P("Mahasiswa,", { noIndent: true, after: 1100 }), P("**As'ad Bahauddin Ahmad**", { noIndent: true, after: 0 }), P("NIM. 230491100034", { noIndent: true })] }),
  ] })] }),
);

// DAFTAR ISI
children.push(new Paragraph({ children: [new PageBreak()] }), C("**DAFTAR ISI**", { after: 240 }),
  new TableOfContents("Daftar Isi", { hyperlink: true, headingStyleRange: "1-3" }),
  P("(Klik kanan pada daftar isi → Update Field → Update entire table untuk memperbarui nomor halaman.)", { noIndent: true, size: 20 }));

// BAB I
children.push(...BAB("BAB I", "PENDAHULUAN"));
children.push(H2("1.1. Latar Belakang"),
  P("Antarmuka perintah suara konvensional umumnya hanya mampu merespons perintah yang terstruktur ketat. Pendekatan berbasis Mel Frequency Cepstral Coefficients (MFCC) dan Convolutional Neural Network (CNN) hanya mengenali kata yang ada pada data latih dan tidak mampu memahami variasi kalimat bebas, sehingga kurang fleksibel untuk lingkungan kerja seperti laboratorium."),
  P("Sejak 2022, penelitian interaksi manusia–robot mulai memanfaatkan _pre-trained Large Language Model_ (LLM) sebagai komponen _Natural Language Understanding_ (NLU). Nwankwo dan Rueckert (2024) menunjukkan bahwa robot otonom yang dikendalikan dengan bahasa alami berbasis LLM dapat memahami instruksi kalimat bebas tanpa data latih intent khusus, tetapi penelitian tersebut memakai Bahasa Inggris. Evaluasi sistematis LLM berukuran kecil untuk perintah robot berbahasa Indonesia yang berjalan sepenuhnya _offline_, beserta perbandingannya dengan metode konvensional, belum banyak dilakukan."),
  P("Laboratorium Sistem Otomasi Universitas Trunojoyo Madura membutuhkan modul pemahaman perintah suara berbahasa Indonesia yang dapat berjalan _offline_ sebagai bagian dari sistem robot pengantar dokumen. Kegiatan Asistensi Hibah Penelitian ini mengevaluasi Qwen2.5 1.5B (kuantisasi Q4_K_M, melalui Ollama) sebagai komponen NLU dalam _pipeline_ Silero VAD → Whisper base → NLU → JSON perintah robot, dengan pembanding _rule-based keyword matching_ dan IndoBERT _fine-tuned_. Evaluasi dilakukan pada 162 ujaran kalimat bebas dari tiga responden dengan tiga tingkat formalitas."),
  H2("1.2. Rumusan Masalah dan Hipotesis"),
  P("Rumusan masalah sesuai proposal:", { noIndent: true }),
  NUM("Seberapa akurat Qwen2.5 dalam mengekstrak intent dari perintah kalimat bebas Bahasa Indonesia secara _fully offline_?"),
  NUM("Berapa _latency end-to-end pipeline_ Whisper + Qwen2.5 dari masukan suara hingga keluaran JSON?"),
  NUM("Bagaimana perbandingan akurasi Qwen2.5 dengan _rule-based keyword matching_ dan IndoBERT _fine-tuned_ pada variasi formalitas kalimat?"),
  P("Hipotesis: (H1) akurasi intent Qwen2.5 di atas 80% untuk kalimat formal dan semi-formal; (H2) Qwen2.5 lebih unggul dari kedua _baseline_ pada kalimat informal; (H3) _latency end-to-end_ di bawah 15 detik. Proposal menetapkan Raspberry Pi 5 sebagai platform; perubahan platform ke laptop dijelaskan pada BAB III.", { before: 60 }),
  H2("1.3. Tujuan"),
  NUM("Mengimplementasikan _pipeline speech recognition_ berbasis Whisper dan mengukur akurasi transkripsinya dengan _Word Error Rate_ (WER).", "angka2"),
  NUM("Mengevaluasi akurasi ekstraksi intent dan entity Qwen2.5 untuk enam kategori intent pada kondisi _fully offline_.", "angka2"),
  NUM("Mengimplementasikan dan mengevaluasi dua metode pembanding: _rule-based keyword matching_ dan IndoBERT _fine-tuned_.", "angka2"),
  NUM("Mengukur _latency end-to-end_ dan ketahanan sistem terhadap variasi formalitas kalimat Bahasa Indonesia.", "angka2"),
);

// BAB II
children.push(...BAB("BAB II", "PELAKSANAAN KEGIATAN"));
children.push(H2("2.1. Waktu dan Tempat Pelaksanaan"),
  P("Kegiatan dilaksanakan di Laboratorium Sistem Otomasi, Program Studi Teknik Mekatronika, Universitas Trunojoyo Madura, pada 24 Agustus–27 November 2026 (tahap pelaksanaan) dan dilanjutkan penyusunan luaran hingga Desember 2026. Seluruh kode, konfigurasi, dan hasil pengujian dikelola dengan Git dan tersimpan di repositori GitHub publik `asadbahauddin/qwen25-indonesian-voice-command-intent`; audio responden tidak diunggah ke repositori untuk menjaga privasi."),
  H2("2.2. Capaian terhadap Jadwal"),
  CAP("Tabel 2.1. Capaian Kegiatan terhadap Jadwal Proposal"),
  T(["No.", "Kegiatan", "Rencana", "Realisasi", "Status"], [
    ["1", "Studi literatur & perancangan sistem", "Agt", "Agt 2026", "Selesai"],
    ["2", "Implementasi pipeline di laptop", "Agt", "Agt–Sep 2026; dibangun ulang dan difinalkan 11–12 Nov 2026", "Selesai"],
    ["3", "Deployment ke Raspberry Pi 5", "Sep", "Tidak terlaksana (microSD rusak, waktu tidak cukup)", "Diganti laptop (BAB III)"],
    ["4", "Baseline rule-based & IndoBERT", "Sep", "Sep 2026; difinalkan 11 Nov 2026", "Selesai"],
    ["5", "Pengumpulan dataset audio", "Sep–Okt", "11–12 Nov 2026 (3 responden, 162 ujaran)", "Selesai, terlambat"],
    ["6", "Pengujian & evaluasi akurasi dan latency", "Okt–Nov", "12 Nov 2026", "Selesai"],
    ["7", "Laporan, poster, artikel, HKI", "Nov–Des", "Mulai 12 Nov 2026", "Berjalan"],
    ["8", "Seminar hasil", "Des", "9–10 Des 2026", "Terjadwal"],
  ], [0.8, 5, 1.6, 5, 2.6]),
  GAP(),
  H2("2.3. Uraian Pelaksanaan Kegiatan"),
  H3("2.3.1. Lingkungan dan Perangkat"),
  P("Pengembangan dan pengujian dilakukan pada laptop MSI (Intel Core i5-12450H, RAM 7,7 GB, GPU NVIDIA RTX 2050 4 GB) secara _fully offline_. Lingkungan Python 3.11 dikelola dengan conda (`mbkm-nlu`), dengan PyTorch 2.14.1 (CUDA 12.6), faster-whisper 1.2.1 (CTranslate2 4.8.2), openai-whisper 20250625, silero-vad 6.2.3, transformers, scikit-learn, dan jiwer 4.0.0. Qwen2.5 1.5B Q4_K_M dijalankan dengan Ollama 0.30.6. Audio direkam dengan mikrofon _wireless lavalier_ dengan _receiver_ USB."),
  H3("2.3.2. Akuisisi Audio"),
  P("Audio direkam pada _sample rate native_ perangkat (48 kHz, WASAPI), digabung menjadi mono, lalu di-_resample_ secara _streaming_ ke 16 kHz (soxr kualitas HQ). Uji mikrofon menunjukkan tidak ada _clipping_ pada sinyal native (RMS ucapan normal −17,35 dBFS) dan bahwa _transmitter_ memiliki _limiter_ dan _noise gate_ (diam ±−91 dBFS), sehingga SNR akustik tidak dapat diukur dari rekaman diam."),
  H3("2.3.3. Voice Activity Detection (VAD)"),
  P("Silero VAD (ONNX) digunakan dengan _state machine_ sendiri: _pre-roll_ 300 ms agar awal kata tidak terpotong, histeresis 0,15, _post-pad_ 200 ms, dan durasi ucapan minimum 250 ms. Waktu komputasi 0,237 ± 0,154 ms per _frame_ 32 ms. Parameter jeda diam (_min_silence_) dipilih dengan **aturan yang ditetapkan sebelum data dikumpulkan** pada data pengembangan terpisah (36 kalimat pilot dan 18 kartu perintah bebas, satu penutur): jeda terkecil dengan ujaran terpecah ≤ 5%, tanpa ujaran terlewat atau terpotong, dan tanpa pemicu palsu. Hasilnya **threshold 0,5 dan min_silence 1200 ms** (2/54 ujaran terpecah, 0 pemicu palsu pada 90 detik suasana lab). Data responden tidak dipakai untuk memilih parameter."),
  H3("2.3.4. Automatic Speech Recognition (Whisper base)"),
  P("Dua implementasi Whisper base dibandingkan. Pada data pengembangan (36 kalimat pilot), WER faster-whisper 38,75% dan openai-whisper 39,58% dengan _initial prompt_ berisi nama entitas domain; tanpa _initial prompt_ WER naik menjadi 56–58%. Karena akurasinya setara tetapi faster-whisper ±3 kali lebih cepat (0,093 vs 0,282 detik per ujaran di GPU), **faster-whisper dipilih** (float16 di GPU, int8 di CPU, _beam_ 5, _temperature_ 0)."),
  H3("2.3.5. NLU Qwen2.5 dan Skema JSON"),
  P("Qwen2.5 1.5B dipanggil melalui HTTP API Ollama dengan _system prompt_ berbahasa Indonesia (6 contoh _few-shot_) dan _structured output_ (JSON Schema), _temperature_ 0, _seed_ 42. Skema keluaran: `intent`, `room`, `object`, `person`, `document`, dan `steps` (daftar sub-perintah khusus `combined_command`). Skema dikunci per intent (v2) sehingga field yang tidak relevan wajib bernilai null. Iterasi _prompt_ dihentikan setelah dua versi untuk mencegah _overfitting_ pada data pengembangan."),
  H3("2.3.6. Metode Pembanding"),
  P("**Rule-based keyword matching** memetakan kata kunci per intent (kamus `config/keywords_id.yaml`) dan memecah perintah majemuk berdasarkan kata penghubung. **IndoBERT** (`indobenchmark/indobert-base-p1`) di-_fine-tune_ untuk klasifikasi intent dengan 300 kalimat latih sintetis (50 per intent); perintah majemuk dipecah per klausa lalu diklasifikasi ulang. Ketiga metode memakai kamus entitas yang sama dan normalisasi yang sama sehingga perbandingan Exact Match adil."),
  H3("2.3.7. Integrasi Pipeline dan Antarmuka"),
  P("Seluruh komponen diintegrasikan dalam satu _pipeline_ dengan antarmuka baris perintah (CLI) interaktif: metode NLU, mode masukan (mikrofon atau teks), model Whisper, _beam size_, dan perangkat (GPU/CPU) dapat diganti tanpa memuat ulang program. Setiap ujaran menampilkan transkrip, JSON, dan tabel _latency_ per tahap, serta dicatat ke log CSV. Contoh keluaran ada pada Lampiran 3."),
  H3("2.3.8. Dataset Responden"),
  P("Tiga responden (bahasa ibu Madura satu orang, Jawa dua orang; usia 20–21 tahun) masing-masing mengucapkan 54 perintah berdasarkan **kartu skenario** (intent dan entitas target serta gaya formalitas), dengan **kalimat mereka sendiri**, bukan membaca kalimat. Total 162 ujaran (27 per intent, 54 per formalitas), WAV 16 kHz mono 16-bit, 13,4 menit. Persetujuan ketiga responden tercatat pada metadata responden (Lampiran 4). Transkrip _ground-truth_ dikoreksi manual dengan bantuan dua draf Whisper dari konfigurasi berbeda untuk mengurangi _anchoring_; label disusun dari apa yang benar-benar diucapkan (entitas yang tidak diucapkan bernilai null). Pemeriksaan kebocoran data menunjukkan tidak ada kalimat yang sama dengan set pilot, data latih IndoBERT, maupun contoh _prompt_; dua kalimat pendek memiliki kemiripan ≥ 0,8 (Jaccard) dan diuji dengan analisis sensitivitas."),
  H3("2.3.9. Prosedur Evaluasi"),
  P("Ketiga metode diuji pada tiga masukan: (1) **teks** _ground-truth_ untuk mengukur galat NLU saja, (2) **rekaman utuh** → Whisper, dan (3) **VAD → Whisper** (pipeline lengkap), masing-masing pada **laptop GPU** dan **laptop CPU**. Metrik: WER, _Intent Accuracy_, _Exact Match_ (intent dan seluruh entitas serta langkah tepat), F1 _weighted_ dan _macro_, _confusion matrix_, persentase JSON valid, serta _latency_ per tahap. Tiga ujaran pertama per platform dijalankan sebagai pemanasan dan tidak dihitung. Perbedaan antarmetode diuji dengan uji McNemar eksak pada item yang sama."),
);

children.push(H2("2.4. Hasil"),
  H3("2.4.1. Latency"),
  P("Tabel 2.2 menyajikan _latency pipeline_ lengkap. Total adalah waktu komputasi (VAD + Whisper + Qwen2.5); waktu respons adalah waktu yang dirasakan pengguna setelah selesai berbicara, yaitu jeda tunggu VAD 1,2 detik ditambah Whisper dan Qwen2.5."),
  CAP("Tabel 2.2. Latency Pipeline per Tahap (rata-rata ± SD, n = 162 ujaran per platform)"),
  T(["Platform", "VAD (s)", "Whisper (s)", "Qwen2.5 (s)", "Total (s)", "Waktu respons (s)"], [
    ["Laptop GPU (RTX 2050)", "0,076 ± 0,088", "0,200 ± 0,114", "1,024 ± 0,433", "1,300 ± 0,604", "2,424 ± 0,528 (maks 4,34)"],
    ["Laptop CPU (i5-12450H)", "0,069 ± 0,056", "1,346 ± 1,231", "2,822 ± 1,825", "4,237 ± 2,826", "5,368 ± 2,791 (maks 26,04)"],
  ], [3.4, 2, 2, 2, 2, 3], { centerCols: [1, 2, 3, 4, 5] }),
  NOTE("Sumber: results/eval_dataset_MSI_20261112_095743.md. Platform Raspberry Pi 5 tidak diuji (BAB III). Waktu NLU pembanding di GPU: rule-based 0,001 ± 0,001 s, IndoBERT 0,037 ± 0,039 s."),
  P("Di laptop GPU seluruh ujaran selesai di bawah 4,4 detik. Di laptop CPU rata-rata waktu respons 5,37 detik, tetapi 4 dari 162 ujaran melebihi 15 detik (maksimum 26,0 detik). Keempatnya terjadi saat RAM tersedia hanya 0,24–0,44 GB, sehingga lonjakan tersebut diduga disebabkan _swap_ memori, bukan beban komputasi model itu sendiri."),
  ...FIG("latency_id.png", 567, 227, "Gambar 2.1. Komposisi waktu komputasi pipeline per tahap (rata-rata, n = 162)"),
  H3("2.4.2. Akurasi Transkripsi (WER)"),
  CAP("Tabel 2.3. WER Whisper base pada 162 Ujaran Responden"),
  T(["Platform", "Masukan", "WER", "Formal", "Semi-formal", "Informal"], [
    ["Laptop GPU", "Rekaman utuh", "31,44%", "34,90%", "31,88%", "27,43%"],
    ["Laptop GPU", "Segmen VAD", "30,78%", "32,96%", "29,28%", "30,00%"],
    ["Laptop CPU", "Rekaman utuh", "32,48%", "35,18%", "33,04%", "29,14%"],
    ["Laptop CPU", "Segmen VAD", "29,83%", "32,69%", "29,28%", "27,43%"],
  ], [2.6, 2.6, 1.8, 1.8, 2.2, 1.8], { centerCols: [2, 3, 4, 5] }),
  NOTE("WER dihitung dengan jiwer setelah normalisasi huruf kecil dan penghapusan tanda baca; n = 54 per formalitas."),
  P("Sekitar satu dari tiga kata salah ditranskripsi oleh Whisper base, terutama nama orang dan kata umum (misalnya \"tolong carikan\" → \"jarikan\"). WER kalimat informal tidak lebih tinggi daripada kalimat formal (27,43% vs 34,90% pada rekaman utuh)."),
  H3("2.4.3. Akurasi Ekstraksi Intent dan Entity"),
  CAP("Tabel 2.4. Akurasi NLU pada Laptop GPU (n = 162 kalimat uji)"),
  T(["Metode", "Masukan", "Jumlah kalimat uji", "Intent Accuracy", "Exact Match", "F1 weighted", "F1 macro"], [
    ["Qwen2.5 1.5B", "Teks", "162", "75,31%", "65,43%", "0,6929", "0,6929"],
    ["Rule-based", "Teks", "162", "85,80%", "85,19%", "0,8395", "0,8395"],
    ["IndoBERT", "Teks", "162", "96,30%", "85,19%", "0,9613", "0,9613"],
    ["Qwen2.5 1.5B", "VAD → Whisper", "162", "62,96%", "45,68%", "0,5843", "0,5843"],
    ["Rule-based", "VAD → Whisper", "162", "65,43%", "61,11%", "0,6381", "0,6381"],
    ["IndoBERT", "VAD → Whisper", "162", "83,95%", "56,17%", "0,8413", "0,8413"],
  ], [2.6, 2.6, 1.8, 1.9, 1.8, 1.7, 1.6], { centerCols: [2, 3, 4, 5, 6] }),
  NOTE("F1 weighted sama dengan F1 macro karena kelas seimbang (27 kalimat per intent). JSON valid 100% untuk semua metode pada masukan ini. Hasil rekaman utuh (tanpa VAD) dan laptop CPU ada di results/eval_dataset_MSI_20261112_095743.md; pada CPU, Qwen teks 78,40% / 70,99%."),
  P("Pada teks _ground-truth_, IndoBERT memperoleh akurasi intent tertinggi (96,30%), diikuti _rule-based_ (85,80%) dan Qwen2.5 (75,31%). Ketika masukan berupa transkrip Whisper, Exact Match turun 19,8 poin (Qwen2.5), 24,1 poin (_rule-based_), dan 29,0 poin (IndoBERT), terutama karena kesalahan transkripsi nama entitas, dan _rule-based_ memperoleh Exact Match tertinggi (61,11%)."),
  ...FIG("akurasi_id.png", 567, 241, "Gambar 2.2. Intent Accuracy dan Exact Match tiga metode pada tiga jenis masukan (laptop GPU, n = 162)"),
  H3("2.4.4. Pengaruh Formalitas dan Responden"),
  CAP("Tabel 2.5. Intent Accuracy / Exact Match per Formalitas, Laptop GPU (%; n = 54 per sel)"),
  T(["Metode", "Masukan", "Formal", "Semi-formal", "Informal"], [
    ["Qwen2.5 1.5B", "Teks", "74,1 / 66,7", "83,3 / 70,4", "68,5 / 59,3"],
    ["Rule-based", "Teks", "85,2 / 85,2", "81,5 / 81,5", "90,7 / 88,9"],
    ["IndoBERT", "Teks", "90,7 / 83,3", "100,0 / 83,3", "98,1 / 88,9"],
    ["Qwen2.5 1.5B", "VAD → Whisper", "59,3 / 46,3", "64,8 / 48,1", "64,8 / 42,6"],
    ["Rule-based", "VAD → Whisper", "59,3 / 57,4", "74,1 / 66,7", "63,0 / 59,3"],
    ["IndoBERT", "VAD → Whisper", "85,2 / 53,7", "87,0 / 61,1", "79,6 / 53,7"],
  ], [3, 3, 2.4, 2.4, 2.4], { centerCols: [2, 3, 4] }),
  ...FIG("formalitas_id.png", 567, 241, "Gambar 2.3. Intent Accuracy per tingkat formalitas (laptop GPU, n = 54 per kelompok)"),
  GAP(),
  CAP("Tabel 2.6. Intent Accuracy / Exact Match per Responden, Pipeline Lengkap, Laptop GPU (%; n = 54)"),
  T(["Metode", "R01 (Madura)", "R02 (Jawa)", "R03 (Jawa)"], [
    ["Qwen2.5 1.5B", "70,4 / 50,0", "55,6 / 40,7", "63,0 / 46,3"],
    ["Rule-based", "72,2 / 63,0", "57,4 / 57,4", "66,7 / 63,0"],
    ["IndoBERT", "85,2 / 57,4", "83,3 / 57,4", "83,3 / 53,7"],
  ], [3.5, 3, 3, 3], { centerCols: [1, 2, 3] }),
  NOTE("Bahasa ibu responden: R01 Madura, R02 dan R03 Jawa. Dengan hanya satu penutur berbahasa ibu Madura, perbedaan antaraksen tidak dapat disimpulkan."),
  H3("2.4.5. Analisis Kesalahan"),
  P("Kesalahan Qwen2.5 terpusat pada dua pola (Tabel 2.7). Pertama, **perintah majemuk** (`combined_command`): dari 27 perintah majemuk, Qwen2.5 hanya mengenali 1 (recall 0,04; F1 0,07 pada teks); sisanya dianggap perintah tunggal, misalnya hanya langkah pertama. Kedua, **perintah umum** (`general_command`, misalnya \"kembali ke posisi semula\") sering dianggap navigasi ke ruangan (13 kasus). F1 Qwen2.5 pada teks untuk `navigate_object`, `find_person`, dan `deliver_document` adalah 0,86–0,96, sedangkan F1 `navigate_room` hanya 0,68 karena menerima limpahan dari kedua pola kesalahan tersebut. IndoBERT unggul pada perintah majemuk (F1 0,88) karena perintah dipecah per klausa sebelum diklasifikasi."),
  CAP("Tabel 2.7. F1 per Intent pada Teks, Laptop GPU"),
  T(["Intent", "Qwen2.5 1.5B", "Rule-based", "IndoBERT"], [
    ["navigate_room", "0,68", "0,93", "0,96"], ["navigate_object", "0,86", "0,91", "0,96"],
    ["find_person", "0,93", "0,85", "1,00"], ["deliver_document", "0,96", "0,88", "0,96"],
    ["combined_command", "0,07", "0,54", "0,88"], ["general_command", "0,65", "0,93", "1,00"],
  ], [4, 3, 3, 3], { centerCols: [1, 2, 3] }),
  NOTE("Sumber: results/analisis_dataset_MSI_20261112_104423.md (juga memuat precision/recall dan masukan VAD → Whisper)."),
  ...FIG("f1_intent_id.png", 567, 227, "Gambar 2.4. F1 per intent pada masukan teks (laptop GPU)"),
  ...FIG("cm_qwen_id.png", 315, 270, "Gambar 2.5. Confusion matrix Qwen2.5 1.5B pada masukan teks: perintah majemuk dan perintah umum sebagian besar diprediksi sebagai perintah tunggal"),
  P("Galat transkripsi berdampak pada ketiga metode: dari kalimat yang Exact Match-nya benar pada teks, 37 (Qwen2.5), 41 (_rule-based_), dan 49 (IndoBERT) menjadi salah ketika masukannya transkrip Whisper, terutama karena nama orang atau ruangan salah dengar."),
  H3("2.4.6. Uji Signifikansi dan Sensitivitas"),
  P("Uji McNemar eksak pada item yang sama menunjukkan bahwa keunggulan IndoBERT atas Qwen2.5 dalam akurasi intent bermakna pada semua masukan dan platform (p < 0,001). Pada transkrip (VAD → Whisper, GPU), akurasi intent Qwen2.5 dan _rule-based_ tidak berbeda bermakna (p = 0,71), sedangkan Exact Match _rule-based_ lebih tinggi secara bermakna dari Qwen2.5 (p = 0,001). Keluaran Qwen2.5 di GPU dan CPU tidak identik walaupun _temperature_ 0 dan _seed_ sama (JSON berbeda pada 13 dari 162 kalimat teks), sehingga hasil dilaporkan per platform. Analisis sensitivitas tanpa dua kalimat yang mirip data latih/_prompt_ mengubah akurasi paling banyak 0,7 poin dan tidak mengubah kesimpulan."),
  H3("2.4.7. Pengujian Hipotesis"),
  CAP("Tabel 2.8. Ringkasan Pengujian Hipotesis (platform laptop)"),
  T(["Hipotesis", "Kriteria", "Hasil", "Keputusan"], [
    ["H1", "Intent accuracy Qwen2.5 formal + semi-formal > 80%", "GPU: 62,04% (pipeline), 78,70% (teks); CPU: 62,96%, 79,63% (n = 108)", "Tidak tercapai"],
    ["H2", "Qwen2.5 lebih unggul dari kedua baseline pada kalimat informal", "Intent informal (pipeline, GPU): Qwen2.5 64,8%, rule-based 63,0%, IndoBERT 79,6%; teks: 68,5 / 90,7 / 98,1%", "Tidak terdukung"],
    ["H3", "Latency end-to-end < 15 s", "GPU: 2,42 ± 0,53 s, semua < 15 s; CPU: 5,37 ± 2,79 s, 4/162 > 15 s", "Tercapai (GPU); sebagian besar tercapai (CPU)"],
  ], [1.6, 4.2, 6, 3]),
  GAP(),
  H2("2.5. Pembahasan"),
  P("Hasil ini menunjukkan bahwa pada domain dengan kosakata terbatas, model kecil yang dilatih khusus (IndoBERT) masih lebih akurat daripada LLM 1,5 miliar parameter yang hanya diarahkan dengan _prompt_. Kelemahan Qwen2.5 bukan pada pemahaman perintah tunggal yang jelas (F1 0,86–0,96 untuk `navigate_object`, `find_person`, dan `deliver_document`), melainkan pada keputusan struktural: mengenali bahwa satu kalimat berisi dua tindakan. Hal ini sejalan dengan temuan uji pendahuluan, ketika kesalahan Qwen2.5 juga dominan pada perintah majemuk."),
  P("Keunggulan _baseline_ pada data pilot (100%) turun pada kalimat bebas responden (_rule-based_ 85,80%, IndoBERT 96,30% pada teks). Penurunan ini menunjukkan pentingnya menguji dengan kalimat bebas, bukan kalimat yang disusun dengan kosakata yang sama dengan kamus atau data latih. Sementara itu, akurasi Qwen2.5 relatif stabil antara pilot (80,56%) dan data responden (75,31%)."),
  P("Dari sisi sistem, galat Whisper base (WER ±31%) menjadi hambatan terbesar: Exact Match turun 20–29 poin ketika teks diganti transkrip. Dari sisi waktu, seluruh _pipeline_ memenuhi batas 15 detik di laptop GPU dengan margin besar, tetapi pada laptop CPU dengan RAM 8 GB terdapat lonjakan akibat kekurangan memori. Ini menjadi pertimbangan penting untuk _deployment_ pada perangkat _embedded_ seperti Raspberry Pi 5."),
);

// BAB III
children.push(...BAB("BAB III", "KENDALA DAN SOLUSI"));
children.push(P("Kendala selama pelaksanaan dan solusinya ditunjukkan pada Tabel 3.1."),
  CAP("Tabel 3.1. Kendala dan Solusi"),
  T(["No.", "Kendala", "Dampak", "Solusi / Tindak Lanjut"], [
    ["1", "Kartu microSD Raspberry Pi 5 rusak (OS gagal booting) dan waktu pelaksanaan tidak cukup", "Rumusan masalah 1–2 dan H1/H3 tidak dapat dijawab untuk Raspberry Pi 5", "Atas keputusan peneliti (12 Nov 2026), seluruh pengujian dilakukan pada laptop secara fully offline, dalam dua skenario: laptop GPU dan laptop CPU (tanpa GPU, sebagai pendekatan perangkat tanpa akselerator). Angka laptop tidak diklaim sebagai kinerja Raspberry Pi 5; pengujian Raspberry Pi 5 menjadi saran penelitian lanjutan/skripsi."],
    ["2", "Pengumpulan dataset terlambat dari jadwal (Sep–Okt)", "Evaluasi set uji baru dapat dilakukan 12 Nov 2026", "Desain kartu skenario dan alat rekam disiapkan sehingga 162 ujaran direkam dalam dua hari; seluruh pengujian selesai sebelum batas 27 Nov 2026."],
    ["3", "Angka pada Tabel 2.2–2.3 Laporan Kemajuan bersifat ilustratif (bukan hasil pengukuran)", "Tidak dapat dibandingkan dengan hasil akhir", "Seluruh angka pada laporan akhir berasal dari eksekusi nyata yang tersimpan di folder results/ repositori (Lampiran 5)."],
    ["4", "RAM laptop 7,7 GB hampir penuh saat model berjalan bersamaan", "Lonjakan latency hingga 26 s pada laptop CPU", "RAM tersedia dicatat per ujaran sehingga pencilan dapat dikenali; disarankan menutup aplikasi lain atau memakai perangkat dengan memori lebih besar."],
    ["5", "Galat pengukuran yang ditemukan saat pengujian: Ollama tetap berjalan di CPU setelah mode CPU; pustaka Silero mengunci PyTorch ke 1 thread; server Ollama mati saat uji", "Angka latency/akurasi bisa keliru tanpa terdeteksi", "num_gpu Ollama ditetapkan eksplisit, jumlah thread dipulihkan, versi Ollama dicek dan evaluasi berhenti otomatis bila Ollama tidak terjangkau."],
    ["6", "Transkrip manual tidak konsisten (kata depan tersambung, salah ketik)", "Ground-truth WER dan masukan teks bisa bias", "Pemeriksaan otomatis + perbaikan dengan persetujuan peneliti; konvensi EYD ditambahkan pada alat koreksi."],
    ["7", "Perubahan skema JSON sejak laporan kemajuan (field destination/sub_commands diganti steps)", "Format keluaran berbeda dari laporan kemajuan", "Skema final (v2) ditetapkan dan disetujui pada 11 Nov 2026, dipakai sama untuk ketiga metode."],
  ], [0.8, 4, 3.6, 6.6]),
);

// BAB IV LUARAN
children.push(...BAB("BAB IV", "LUARAN"));
children.push(P("Status luaran wajib dan luaran tambahan sesuai Buku Pedoman Program Asistensi Hibah Penelitian ditunjukkan pada Tabel 4.1."),
  CAP("Tabel 4.1. Status Luaran"),
  T(["No.", "Luaran", "Jenis", "Status"], [
    ["1", "Laporan akhir", "Wajib", "Draf (dokumen ini)"],
    ["2", "Dokumentasi kegiatan", "Wajib", "Tangkapan layar tersedia; foto kegiatan [ISI] (Lampiran 2)"],
    ["3", "Artikel ilmiah – Journal of Technology and Informatics (JoTI), SINTA 3", "Wajib", "Disusun dalam Bahasa Inggris sesuai pedoman JoTI (maks. 10 halaman, IEEE); target submit [ISI] Desember 2026"],
    ["4", "Hak Kekayaan Intelektual (hak cipta)", "Wajib", "Jenis ciptaan menunggu keputusan pembimbing (Subbab 4.1); berkas disiapkan"],
    ["5", "Logbook kegiatan", "Wajib", "Berjalan (Lampiran 1)"],
    ["6", "Kontribusi pada luaran penelitian dosen", "Wajib", "Modul NLU, dataset, dan hasil evaluasi untuk penelitian robot pengantar dokumen [ISI: sesuaikan dengan penelitian dosen]"],
    ["7", "Poster ilmiah", "Tambahan", "Disusun dari hasil evaluasi"],
    ["8", "Dataset penelitian (162 ujaran berlabel + data card)", "Tambahan", "Selesai dikumpulkan dan dilabeli; paket dan data card disiapkan"],
  ], [0.8, 6, 1.8, 6.4]),
  GAP(),
  H2("4.1. Rencana Hak Kekayaan Intelektual"),
  P("Pengajuan dilakukan melalui sistem e-HKI Universitas Trunojoyo Madura (https://hki.trunojoyo.ac.id/) dengan jenis permohonan **Lembaga Pendidikan**. Dua jenis ciptaan dapat diajukan dari kegiatan ini (Tabel 4.2); keputusan jenis ciptaan dan susunan pencipta diserahkan kepada dosen pembimbing."),
  CAP("Tabel 4.2. Pilihan Ciptaan untuk Hak Cipta"),
  T(["Aspek", "Opsi A: Program Komputer", "Opsi B: Dataset"], [
    ["Jenis / sub jenis (e-HKI)", "Karya Lainnya / Program Komputer", "Karya Lainnya / Basis Data atau Kompilasi Ciptaan/Data"],
    ["Ciptaan", "Perangkat lunak pipeline perintah suara (VAD, ASR, 3 metode NLU, CLI, alat evaluasi); ±4.600 baris Python", "162 ujaran audio berlabel transkrip, intent, entitas, formalitas, dan data card"],
    ["Contoh ciptaan", "Source code lengkap (±350 KB, di bawah batas 10 MB)", "Berkas dataset/kompilasi data [perlu konfirmasi LPPM: bentuk bukti untuk basis data]"],
    ["Bukti publikasi", "PDF tangkapan layar setiap bagian aplikasi beserta keterangan dan pseudocode", "[perlu konfirmasi LPPM]"],
    ["Catatan", "Repositori GitHub publik (commit pertama 9 Okt 2026) dapat menjadi dasar tanggal pengumuman", "Sesuai rencana pada laporan kemajuan dan lembar persetujuan responden; audio berisi suara responden (privasi)"],
  ], [3.4, 5.8, 5.8]),
  NOTE("Ketentuan dari Panduan Hak Cipta e-HKI UTM: login SSO, profil lengkap (KTP berwarna, tanda tangan digital), pemohon menjadi Ketua Pencipta, pencipta lain menerima undangan dari akunnya, Surat Pernyataan dan Surat Pengalihan Hak Cipta ber-e-Meterai setelah validasi LPPM, dan pembayaran kode billing DJKI pada hari yang sama sebelum pukul 23.59."),
  P("[KEPUTUSAN PEMBIMBING: jenis ciptaan (A/B/keduanya), Ketua Pencipta, susunan pencipta, dan sumber biaya pendaftaran]", { noIndent: true }),
  H2("4.2. Artikel Ilmiah"),
  P("Artikel berjudul [ISI: judul artikel, maks. 15 kata, Bahasa Inggris] disusun untuk Journal of Technology and Informatics (JoTI) Universitas Dinamika (SINTA 3), yang ruang lingkupnya mencakup _Artificial Intelligence_ dan _Robotics Systems_. Isi artikel mengikuti Bab II laporan ini: rancangan _pipeline_, dataset kalimat bebas, perbandingan tiga metode, dan analisis kesalahan."),
);

// BAB V KESIMPULAN
children.push(...BAB("BAB V", "KESIMPULAN"));
children.push(
  NUM("Pada 162 ujaran kalimat bebas dari tiga responden, Qwen2.5 1.5B (Q4_K_M, _fully offline_ pada laptop) mencapai _Intent Accuracy_ 75,31% dan _Exact Match_ 65,43% pada teks _ground-truth_, serta 62,96% dan 45,68% pada _pipeline_ lengkap (VAD → Whisper → Qwen2.5). Target H1 (> 80% untuk formal dan semi-formal) tidak tercapai (78,70% pada teks; 62,04% pada _pipeline_).", "simpul"),
  NUM("_Latency end-to-end pipeline_ pada laptop GPU adalah 1,30 ± 0,60 detik waktu komputasi dan 2,42 ± 0,53 detik waktu respons (maksimum 4,34 detik), sehingga H3 tercapai. Pada laptop CPU waktu respons 5,37 ± 2,79 detik, dengan 4 dari 162 ujaran melebihi 15 detik akibat keterbatasan memori.", "simpul"),
  NUM("IndoBERT _fine-tuned_ memberikan akurasi intent tertinggi (96,30% teks; 83,95% _pipeline_), sedangkan _rule-based_ memberikan _Exact Match_ tertinggi pada transkrip (61,11%). Pada kalimat informal, Qwen2.5 tidak lebih unggul dari kedua pembanding, sehingga H2 tidak terdukung. Kelemahan utama Qwen2.5 adalah mengenali perintah majemuk (recall 0,04).", "simpul"),
  NUM("Whisper base dengan _initial prompt_ domain menghasilkan WER 31,44% (rekaman utuh) dan 30,78% (segmen VAD). Galat transkripsi menurunkan _Exact Match_ ketiga metode sebesar 20–29 poin dan merupakan sumber galat terbesar _pipeline_.", "simpul"),
  H2("Saran"),
  BUL("Memperbaiki penanganan perintah majemuk pada Qwen2.5, misalnya pemecahan klausa sebelum LLM, contoh _few-shot_ majemuk yang lebih banyak, atau model lebih besar (Qwen2.5 3B), dengan set pengembangan baru agar tidak menyetel pada data uji ini."),
  BUL("Meningkatkan akurasi ASR dengan Whisper small atau _fine-tuning_ Whisper untuk Bahasa Indonesia dan kosakata laboratorium."),
  BUL("Menguji _pipeline_ pada Raspberry Pi 5 sesuai rencana awal, termasuk suhu dan _throttling_, serta mengintegrasikan keluaran JSON ke sistem robot pengantar dokumen (tahap skripsi)."),
  BUL("Menambah jumlah dan keragaman responden (aksen Madura dan Jawa yang seimbang, responden yang tidak mengenal sistem)."),
);

// DAFTAR PUSTAKA
children.push(new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "DAFTAR PUSTAKA", font: FONT, size: 24, bold: true })], spacing: { after: 240 } }));
[
  "Adila, A., Lestari, D., Purwarianti, A., Tanaya, D., Azizah, K., & Sakti, S. (2024). Enhancing Indonesian automatic speech recognition: Evaluating multilingual models with diverse speech variabilities. _arXiv_. https://arxiv.org/abs/2410.08828",
  "Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. _Proceedings of NAACL-HLT 2019_, 4171–4186.",
  "Fathony, I. A. N., Mareta, A., Adiana, B. E., Wardhani, O., & Halim, D. A. (2025). Optimisasi Whisper speech-to-text Bahasa Indonesia dengan hybrid cloud dan multi-engine. _ELKOM: Jurnal Elektronika dan Komputer, 18_(1), 60–72. https://doi.org/10.51903/5n2d3s08",
  "McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. _Psychometrika, 12_(2), 153–157.",
  "Nwankwo, L., & Rueckert, E. (2024). The conversation is the command: Interacting with real-world autonomous robots through natural language. _Companion of the 2024 ACM/IEEE International Conference on Human-Robot Interaction (HRI '24)_, 284–288. https://doi.org/10.1145/3610978.3640723",
  "Qwen Team, Alibaba Group. (2024). Qwen2.5 technical report. _arXiv_. https://arxiv.org/abs/2412.15115",
  "Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2023). Robust speech recognition via large-scale weak supervision. _Proceedings of the 40th International Conference on Machine Learning (PMLR 202)_. https://proceedings.mlr.press/v202/radford23a.html",
  "Silero Team. (2024). _Silero VAD: Pre-trained enterprise-grade voice activity detector_ [Computer software]. GitHub. https://github.com/snakers4/silero-vad",
  "SYSTRAN. (2024). _faster-whisper: Faster Whisper transcription with CTranslate2_ [Computer software]. GitHub. https://github.com/SYSTRAN/faster-whisper",
  "Wilie, B., Vincentio, K., Winata, G. I., Cahyawijaya, S., Li, X., Lim, Z. Y., … Purwarianti, A. (2020). IndoNLU: Benchmark and resources for evaluating Indonesian natural language understanding. _Proceedings of the 1st Conference of the Asia-Pacific Chapter of the ACL_. https://aclanthology.org/2020.aacl-main.85/",
].forEach((r) => children.push(new Paragraph({ children: runs(r), alignment: AlignmentType.LEFT, indent: { left: 720, hanging: 720 }, spacing: { line: 240, after: 120 } })));

// LAMPIRAN
children.push(new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "LAMPIRAN", font: FONT, size: 24, bold: true })], spacing: { after: 240 } }),
  H2("Lampiran 1. Logbook Kegiatan Mahasiswa"),
  T(["No.", "Hari/Tanggal", "Deskripsi Kegiatan", "Bukti", "Paraf"], [
    ["1", "24–28 Agt 2026", "Studi literatur (Whisper, Qwen2.5, Nwankwo & Rueckert, IndoNLU); perancangan arsitektur pipeline, enam intent, skema JSON.", "study literatus.png", ""],
    ["2", "31 Agt–4 Sep 2026", "Penyiapan lingkungan pengembangan; akuisisi audio dan VAD.", "Penyiapan lingkungan pengembangan.png", ""],
    ["3", "7–11 Sep 2026", "Integrasi pipeline VAD → Whisper → Qwen2.5; system prompt JSON.", "integrasi pipeline VAD.png", ""],
    ["4", "14–18 Sep 2026", "Baseline rule-based keyword matching.", "implementasi baseline rule-based.png", ""],
    ["5", "21–25 Sep 2026", "Data latih berlabel dan fine-tuning IndoBERT.", "Penyusunan data latih.png", ""],
    ["6", "28 Sep–2 Okt 2026", "Persiapan deployment RPi 5; microSD rusak.", "[ISI]", ""],
    ["7", "5–9 Okt 2026", "Revisi proposal dan penyusunan laporan kemajuan.", "[ISI]", ""],
    ["8–12", "12 Okt–6 Nov 2026", "[ISI: kegiatan sebenarnya per minggu, termasuk monev LPPM 12–16 Okt]", "[ISI]", ""],
    ["13", "9–13 Nov 2026", "Audit dan migrasi lingkungan (conda); uji mikrofon; finalisasi NLU Qwen2.5 dan baseline; uji pilot 36 kalimat; perekaman 3 responden (162 ujaran); Silero VAD dan pemilihan parameter dari data pengembangan; perbandingan Whisper; pipeline + CLI; transkripsi dan pelabelan; evaluasi set uji dan analisis.", "F0–F9 bukti (Dokumentasi/), [ISI: foto]", ""],
    ["14–16", "16 Nov–5 Des 2026", "[ISI: penyusunan poster, artikel JoTI, berkas HKI, laporan akhir]", "[ISI]", ""],
  ], [1, 2.8, 7.2, 3.2, 1.3]),
  GAP(),
  H2("Lampiran 2. Dokumentasi Kegiatan"),
  P("[ISI: foto perangkat (mikrofon lavalier, receiver, laptop), sesi perekaman responden, CLI saat mode mikrofon, bimbingan. Tangkapan layar yang sudah tersedia: Dokumentasi/F0_bukti_cek_env.png, F1_bukti_tes_mic.png, dan lima tangkapan layar kegiatan Agustus–September.]", { noIndent: true }),
  H2("Lampiran 3. Contoh Keluaran Sistem"),
  P("Contoh dari set pilot (pengembangan). Perintah \"Silakan temukan Ibu Vivi.\" menghasilkan keluaran Qwen2.5:", { noIndent: true }),
  P('{"intent": "find_person", "room": null, "object": null, "person": "bu vivi", "document": null, "steps": null}', { noIndent: true, size: 20 }),
  P("Waktu NLU 0,598 s (laptop GPU; load 0,158 s, prompt eval 0,026 s, eval 0,394 s, 73,5 token/s). [ISI: tangkapan layar CLI]", { noIndent: true }),
  H2("Lampiran 4. Lembar Persetujuan Responden"),
  P("Templat lembar persetujuan: Dokumentasi/F8_lembar_persetujuan.md. [ISI: pindaian lembar bertanda tangan R01–R03; jangan diunggah ke repositori publik karena memuat nama.]", { noIndent: true }),
  H2("Lampiran 5. Daftar Berkas Hasil Pengujian"),
  T(["Pengujian", "Berkas (folder results/ repositori)"], [
    ["Uji mikrofon", "mic_MSI_20261111_222034.md"], ["Kualitas dataset", "kualitas_dataset_MSI_20261112_005606.md"],
    ["VAD (karakterisasi, data pengembangan)", "vad_MSI_20261112_014026.md; vad_dev_MSI_20261112_041005.md"],
    ["Whisper (latency, WER pilot)", "asr_MSI_20261112_010730.md; asr_pilot_MSI_20261112_041011.md"],
    ["Uji pendahuluan NLU (pilot)", "summary_MSI_20261111_225631.md; summary_MSI_20261111_230143.md; eval_pilot_MSI_20261112_042305.md"],
    ["Cek kebocoran data", "kebocoran_MSI_20261112_095154.md"],
    ["Evaluasi set uji", "eval_dataset_MSI_20261112_095743.md"], ["Analisis lanjutan", "analisis_dataset_MSI_20261112_104423.md"],
  ], [6, 9]),
);

const doc = new Document({
  creator: "As'ad Bahauddin Ahmad", title: "Laporan Akhir Asistensi Hibah Penelitian",
  styles: {
    default: { document: { run: { font: FONT, size: 24 }, paragraph: { spacing: { line: 240 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 24, bold: true }, paragraph: { spacing: { before: 0, after: 120 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 24, bold: true }, paragraph: { spacing: { before: 120, after: 80 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 24, bold: true }, paragraph: { spacing: { before: 80, after: 60 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    ...["angka", "angka2", "simpul"].map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567, hanging: 397 } } } }] })),
    { reference: "titik", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567, hanging: 397 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: 4 * CM, bottom: 3 * CM, left: ML, right: MR } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 22 })] })] }) },
    children,
  }],
});
const out = process.argv[2];
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(out, b); console.log("ditulis", out, b.length, "byte"); });
