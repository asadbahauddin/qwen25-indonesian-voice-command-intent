// Dokumen sumber foto kegiatan untuk luaran/sisip_ke_laporan.py (operasi foto_kegiatan).
// Foto ada di luaran/foto/ (tidak di-push; nama file netral, keterangan memakai kode responden, bukan nama).
//   node luaran/buat_sumber_foto.js <keluaran.docx>
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, ImageRun, AlignmentType } = require("docx");
const FONT = "Times New Roman";
const F = path.join(__dirname, "foto");
const fig = (file, w, cap) => {
  const buf = fs.readFileSync(path.join(F, file));
  const h = Math.round(w * buf.readUInt32BE(20) / buf.readUInt32BE(16));
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h }, altText: { title: cap, description: cap, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [new TextRun({ text: cap, font: FONT, size: 22 })] }),
  ];
};
const doc = new Document({ sections: [{ children: [
  new Paragraph({ children: [new TextRun("SISIP_FOTO_MULAI")] }),
  ...fig("rekam_R01.png", 240, "Gambar L.6. Perekaman suara responden R01 dengan mikrofon lavalier di Laboratorium Sistem Otomasi"),
  ...fig("rekam_R02.png", 240, "Gambar L.7. Perekaman suara responden R02"),
  ...fig("rekam_R03.png", 240, "Gambar L.8. Perekaman suara responden R03 (peneliti)"),
  ...fig("koding_label.png", 240, "Gambar L.9. Pengodean program, transkripsi, dan pelabelan data"),
  new Paragraph({ children: [new TextRun("SISIP_FOTO_SELESAI")] }),
] }] });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[2], b); console.log("ditulis", process.argv[2]); });
