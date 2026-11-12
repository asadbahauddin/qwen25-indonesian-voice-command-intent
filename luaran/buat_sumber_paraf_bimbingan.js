// Sumber untuk sisip_ke_laporan.py: paraf pembimbing (operasi paraf_logbook; atas izin Bu Vivi, 12 Nov 2026)
// dan foto bimbingan (operasi foto_bimbingan). Berkas di luaran/foto/ (tidak di-push).
//   node luaran/buat_sumber_paraf_bimbingan.js <keluaran.docx>
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, ImageRun, AlignmentType } = require("docx");
const F = path.join(__dirname, "foto");
const FONT = "Times New Roman";
function ukuranJpeg(b) {           // baca lebar x tinggi dari penanda SOFn JPEG
  let i = 2;
  while (i < b.length) {
    const m = b[i + 1], len = b.readUInt16BE(i + 2);
    if (m >= 0xc0 && m <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(m)) return [b.readUInt16BE(i + 7), b.readUInt16BE(i + 5)];
    i += 2 + len;
  }
  throw new Error("ukuran JPEG tidak terbaca");
}
const img = (file, w, alt) => {
  const buf = fs.readFileSync(path.join(F, file)); const [W, H] = ukuranJpeg(buf);
  return new ImageRun({ type: "jpg", data: buf, transformation: { width: w, height: Math.round(w * H / W) }, altText: { title: alt, description: alt, name: file } });
};
const cap = "Gambar L.10. Kegiatan bimbingan dengan dosen pembimbing";
const doc = new Document({ sections: [{ children: [
  new Paragraph({ children: [new TextRun("SISIP_LB_ttd")] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 0 }, children: [img("paraf_pembimbing.jpeg", 40, "Paraf pembimbing")] }),
  new Paragraph({ children: [new TextRun("SISIP_BIMBINGAN_MULAI")] }),
  new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 }, children: [img("bimbingan.jpeg", 200, cap)] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [new TextRun({ text: cap, font: FONT, size: 22 })] }),
  new Paragraph({ children: [new TextRun("SISIP_BIMBINGAN_SELESAI")] }),
] }] });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[2], b); console.log("ditulis", process.argv[2]); });
