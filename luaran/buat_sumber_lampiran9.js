// Sumber "Lampiran 9. Poster Ilmiah" untuk luaran/sisip_ke_laporan.py (operasi lampiran9).
// Gambar = luaran/poster/poster_pratinjau.png (render dari luaran/buat_poster.py; angka dibaca dari results/).
//   node luaran/buat_sumber_lampiran9.js <keluaran.docx>
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, ImageRun, AlignmentType, HeadingLevel, PageBreak } = require("docx");
const FONT = "Times New Roman";
const buf = fs.readFileSync(path.join(__dirname, "poster", "poster_pratinjau.png"));
const w = 470, h = Math.round(w * buf.readUInt32BE(20) / buf.readUInt32BE(16));
const cap = "Gambar L.14. Poster ilmiah penelitian (ukuran A1 tegak, 594 × 841 mm)";
const T = (t, o = {}) => new TextRun({ text: t, font: FONT, size: 24, ...o });
const doc = new Document({ sections: [{ children: [
  new Paragraph({ children: [new TextRun("SISIP_L9_MULAI")] }),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 120, after: 80 }, children: [T("Lampiran 9. Poster Ilmiah", { bold: true })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { firstLine: 720 }, spacing: { after: 120 }, children: [
    T("Poster disusun sebagai luaran tambahan dengan ukuran A1 tegak (berkas luaran/poster/poster.pdf). Seluruh angka pada poster dibaca otomatis dari berkas hasil evaluasi set uji (results/eval_dataset_MSI_20261112_095743.json dan results/analisis_dataset_MSI_20261112_104423.json), bukan diketik ulang. Poster tidak memuat wajah atau nama responden.")] }),
  new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 60, after: 60 },
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h }, altText: { title: cap, description: cap, name: "poster.png" } })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [T(cap, { size: 22 })] }),
  new Paragraph({ children: [new TextRun("SISIP_L9_SELESAI")] }),
] }] });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[2], b); console.log("ditulis", process.argv[2]); });
