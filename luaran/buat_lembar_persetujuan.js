// Lembar persetujuan responden siap cetak (satu halaman per responden), dari Dokumentasi/F8_lembar_persetujuan.md.
// Kode responden & tanggal perekaman dari dataset/responden.csv; nama, tanggal tanda tangan, dan tanda tangan DIKOSONGKAN
// (diisi saat penandatanganan, dengan tanggal sebenarnya).
//   node luaran/buat_lembar_persetujuan.js Lembar_Persetujuan_Responden.docx
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, AlignmentType, WidthType, BorderStyle,
  LevelFormat, PageBreak } = require("docx");

const FONT = "Times New Roman";
const TW = 11906 - 2 * 1418;
const rows = fs.readFileSync(path.join(__dirname, "..", "dataset", "responden.csv"), "utf-8").trim().split(/\r?\n/);
const head = rows[0].split(",");
const resp = rows.slice(1).map((l) => Object.fromEntries(l.split(",").map((v, i) => [head[i], v])));
const BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const tgl = (iso) => { const [y, m, d] = iso.split("-").map(Number); return `${d} ${BULAN[m - 1]} ${y}`; };

const T = (text, o = {}) => new TextRun({ text, font: FONT, size: o.size || 22, bold: o.bold, italics: o.italics });
const P = (parts, o = {}) => new Paragraph({ children: Array.isArray(parts) ? parts : [T(parts, o)], alignment: o.align || AlignmentType.JUSTIFIED,
  spacing: { after: o.after === undefined ? 80 : o.after }, numbering: o.num ? { reference: "n", level: 0 } : undefined });
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const line = { style: BorderStyle.SINGLE, size: 4, color: "000000" };

const POIN = [
  ["Tujuan. ", "Penelitian ini menguji kemampuan program komputer dalam memahami perintah suara berbahasa Indonesia yang ditujukan kepada robot."],
  ["Yang Anda lakukan. ", "Anda melihat ±54 kartu skenario (misalnya \"minta robot mengantar dokumen kepada seseorang\"), lalu mengucapkan perintah tersebut dengan kalimat Anda sendiri ke mikrofon clip-on. Waktu yang dibutuhkan ±20–30 menit."],
  ["Data yang direkam. ", "Suara Anda dalam bentuk file audio, ditambah usia, jenis kelamin, dan bahasa ibu. Nama Anda tidak disimpan bersama rekaman; rekaman hanya diberi kode anonim (mis. R01)."],
  ["Penggunaan data. ", "Rekaman dan transkripnya dipakai untuk penelitian ini dan untuk dataset yang dapat didaftarkan sebagai Hak Kekayaan Intelektual atas nama tim peneliti. Data dapat dipakai untuk publikasi ilmiah, laporan, dan penelitian lanjutan tanpa mencantumkan identitas Anda."],
  ["Penyimpanan. ", "Audio disimpan di perangkat peneliti dan penyimpanan cloud pribadi, tidak diunggah ke repositori publik tanpa persetujuan tambahan."],
  ["Sukarela. ", "Partisipasi bersifat sukarela. Anda boleh berhenti kapan saja tanpa konsekuensi dan boleh meminta rekaman Anda dihapus dengan menghubungi peneliti."],
  ["Risiko. ", "Tidak ada risiko yang diketahui selain waktu yang Anda luangkan."],
];

function halaman(r, terakhir) {
  const isian = [["Kode responden", r.penutur], ["Tanggal perekaman", tgl(r.tanggal)], ["Nama lengkap", ""],
    ["Tanggal penandatanganan", "____ / ____ / 2026"], ["Tanda tangan responden", ""], ["Tanda tangan peneliti", ""]];
  const tbl = new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: [3400, TW - 3400], rows: isian.map(([k, v], i) =>
    new TableRow({ height: { value: i >= 4 ? 900 : 480, rule: "atLeast" }, children: [
      new TableCell({ width: { size: 3400, type: WidthType.DXA }, borders: { top: none, left: none, right: none, bottom: none },
        children: [P([T(k)], { after: 0, align: AlignmentType.LEFT })] }),
      new TableCell({ width: { size: TW - 3400, type: WidthType.DXA }, borders: { top: none, left: none, right: none, bottom: line },
        children: [P([T(v, { bold: true })], { after: 0, align: AlignmentType.LEFT })] }),
    ] })) });
  return [
    P([T("LEMBAR PERSETUJUAN RESPONDEN", { bold: true, size: 26 })], { align: AlignmentType.CENTER, after: 0 }),
    P([T("Perekaman Suara untuk Dataset Penelitian", { size: 22 })], { align: AlignmentType.CENTER, after: 200 }),
    P([T("Judul penelitian: ", { bold: true }), T("Evaluasi Large Language Model Qwen2.5 untuk Ekstraksi Intent Perintah Kalimat Bebas Bahasa Indonesia pada Robot")]),
    P([T("Peneliti: ", { bold: true }), T("As'ad Bahauddin Ahmad (Teknik Mekatronika, Universitas Trunojoyo Madura)")], { after: 0 }),
    P([T("Pembimbing: ", { bold: true }), T("Ir. Vivi Tri Widyaningrum, S.Kom., M.T.")], { after: 0 }),
    P([T("Program: ", { bold: true }), T("Asistensi Hibah Penelitian (MBKM Riset), LPPM Universitas Trunojoyo Madura")], { after: 0 }),
    P([T("Lokasi: ", { bold: true }), T("Laboratorium Sistem Otomasi, Teknik Mekatronika UTM")], { after: 160 }),
    P([T("Penjelasan kepada responden", { bold: true })]),
    ...POIN.map(([a, b]) => P([T(a, { bold: true }), T(b)], { num: true })),
    P([T("Pernyataan persetujuan", { bold: true })], { after: 60 }),
    P("Saya telah membaca dan memahami penjelasan di atas, mendapat kesempatan bertanya, dan bersedia suara saya direkam serta dipakai sesuai penjelasan tersebut.", { after: 160 }),
    tbl,
    P([T("Lembar ini disimpan peneliti secara terpisah dari data rekaman. Hanya kode responden yang menghubungkan keduanya.", { italics: true, size: 18 })],
      { after: 0 }),
    ...(terakhir ? [] : [new Paragraph({ children: [new PageBreak()] })]),
  ];
}

const doc = new Document({
  numbering: { config: [{ reference: "n", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 400, hanging: 400 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1418, right: 1418 } } },
    children: resp.flatMap((r, i) => halaman(r, i === resp.length - 1)) }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[2], b); console.log("ditulis", process.argv[2], resp.map((r) => r.penutur).join(", ")); });
