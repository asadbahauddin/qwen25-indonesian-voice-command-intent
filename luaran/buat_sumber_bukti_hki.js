// Sumber Gambar 4.1 (bukti pengajuan e-HKI) untuk luaran/sisip_ke_laporan.py (operasi bukti_hki).
// luaran/foto/bukti_pengajuan_hki.png = potongan tangkapan layar peneliti (tanpa alamat, tanda tangan, bilah bookmark).
//   node luaran/buat_sumber_bukti_hki.js <keluaran.docx>
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, ImageRun, AlignmentType } = require("docx");
const FONT = "Times New Roman";
const file = path.join(__dirname, "foto", "bukti_pengajuan_hki.png");
const buf = fs.readFileSync(file);
const w = 528, h = Math.round(w * buf.readUInt32BE(20) / buf.readUInt32BE(16));
const cap = "Gambar 4.1. Bukti pengajuan hak cipta program komputer pada sistem e-HKI UTM (langkah 3 dari 4: menunggu konfirmasi Kepala LPPM)";
const doc = new Document({ sections: [{ children: [
  new Paragraph({ children: [new TextRun("SISIP_HKI_MULAI")] }),
  new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h }, altText: { title: cap, description: cap, name: "bukti_pengajuan_hki.png" } })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [new TextRun({ text: cap, font: FONT, size: 22 })] }),
  new Paragraph({ children: [new TextRun("SISIP_HKI_SELESAI")] }),
] }] });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[2], b); console.log("ditulis", process.argv[2]); });
