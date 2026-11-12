// Gambar kecil untuk kolom Bukti logbook (Lampiran 1), dipakai luaran/sisip_ke_laporan.py operasi logbook:<json>.
// Tiap gambar didahului paragraf penanda SISIP_LB_<kunci>. Foto di luaran/foto/ (tidak di-push).
//   node luaran/buat_sumber_logbook.js <keluaran.docx>
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, ImageRun, AlignmentType } = require("docx");
const F = path.join(__dirname, "foto");
const G = { lk_literatur: "lk_literatur.png", lk_lingkungan: "lk_lingkungan.png", lk_pipeline: "lk_pipeline.png", lk_rule: "lk_rule.png",
  lk_datalatih: "lk_datalatih.png", rpi5: "foto_rpi5.png", f0: "lb_f0.png", f1: "lb_f1.png", koding: "koding_label.png",
  r01: "rekam_R01.png", r02: "rekam_R02.png", r03: "rekam_R03.png", poster: "lb_poster.png", hki: "bukti_pengajuan_hki.png" };
const W = 95, HMAX = 80;   // kotak maksimum 95 x 80 px (gambar potret diperkecil)
const ch = [];
for (const [k, f] of Object.entries(G)) {
  const buf = fs.readFileSync(path.join(F, f));
  let w = W, h = Math.round(W * buf.readUInt32BE(20) / buf.readUInt32BE(16));
  if (h > HMAX) { w = Math.round(w * HMAX / h); h = HMAX; }
  ch.push(new Paragraph({ children: [new TextRun("SISIP_LB_" + k)] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 20, after: 20 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h }, altText: { title: "Bukti " + k, description: "Bukti logbook " + k, name: f } })] }));
}
Packer.toBuffer(new Document({ sections: [{ children: ch }] })).then((b) => { fs.writeFileSync(process.argv[2], b); console.log("ditulis", process.argv[2]); });
