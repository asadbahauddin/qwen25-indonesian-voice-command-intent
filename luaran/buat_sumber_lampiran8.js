// Sumber "Lampiran 8. Draf Artikel Ilmiah" (teks Word biasa, gaya laporan) untuk luaran/sisip_ke_laporan.py (operasi lampiran8).
// Isi = persis isi luaran/buat_artikel_joti.py (diekspor ke JSON), sehingga sama dengan Artikel_JoTI_DRAF.docx.
//   node luaran/buat_sumber_lampiran8.js <artikel_isi.json> <keluaran.docx>
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, BorderStyle, AlignmentType, HeadingLevel,
  ImageRun, TabStopType, Tab, VerticalAlign } = require("docx");
const A = JSON.parse(fs.readFileSync(process.argv[2], "utf-8"));
const FONT = "Times New Roman";
const TW = 11906 - 7 * 567;
const GBR = path.join(__dirname, "gambar");
function runs(text, o = {}) {
  const out = []; const re = /(\*\*[^*]+\*\*|(?<![\w])_[^_]+?_(?![\w]))/g; let last = 0, m;
  const mk = (t, b, i) => new TextRun({ text: t, font: FONT, size: o.size || 24, bold: b || o.bold, italics: i || o.italics });
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(mk(text.slice(last, m.index)));
    out.push(m[0].startsWith("**") ? mk(m[0].slice(2, -2), true) : mk(m[0].slice(1, -1), false, true));
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(mk(text.slice(last)));
  return out;
}
const P = (t, o = {}) => new Paragraph({ alignment: o.align || AlignmentType.JUSTIFIED, spacing: { after: o.after ?? 80 },
  indent: o.first === false ? undefined : { firstLine: 720 }, keepNext: o.keepNext, children: runs(t, o) });
const C = (t, o = {}) => P(t, { ...o, align: AlignmentType.CENTER, first: false });
const B = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const N = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const children = [
  new Paragraph({ children: [new TextRun("SISIP_L8_MULAI")] }),
  new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 120, after: 80 }, children: [new TextRun({ text: "Lampiran 8. Draf Artikel Ilmiah (Journal of Technology and Informatics)", font: FONT, size: 24, bold: true })] }),
  P("Draf artikel berikut disusun mengikuti template JoTI 2025 (berkas terpisah Artikel_JoTI_DRAF.docx dengan huruf Segoe UI dan tata letak jurnal). Pada lampiran ini isinya disajikan dalam format laporan.", { after: 200 }),
  C(`**${A.judul}**`, { size: 28, after: 100 }),
  C("As'ad Bahauddin Ahmad¹*, Vivi Tri Widyaningrum²", { bold: true, after: 40 }),
  C("¹,²Program Studi Teknik Mekatronika, Universitas Trunojoyo Madura, Bangkalan, Jawa Timur, Indonesia", { size: 22, after: 200 }),
  P("**Abstract:**", { first: false, after: 40 }),
  P(A.abstrak, { first: false, italics: true, size: 22, after: 80 }),
  P(`**Keywords:** _${A.kata_kunci}_`, { first: false, size: 22, after: 200 }),
];
let fig = 0;
for (const it of A.isi) {
  const [k] = it;
  if (k === "H") children.push(P(`**${it[1]}**`, { first: false, keepNext: true, after: 60 }));
  else if (k === "S") children.push(P(`**${it[1]}**`, { first: false, keepNext: true, after: 40 }));
  else if (k === "SS") children.push(P(`**_${it[1]}_**`, { first: false, keepNext: true, after: 40 }));
  else if (k === "P") children.push(P(it[1]));
  else if (k === "EQ") children.push(new Paragraph({ tabStops: [{ type: TabStopType.CENTER, position: Math.round(TW / 2) }, { type: TabStopType.RIGHT, position: TW }],
    spacing: { before: 60, after: 60 }, children: [new TextRun({ children: [new Tab()] }), new TextRun({ text: it[1], font: FONT, size: 24, italics: true }),
      new TextRun({ children: [new Tab(), `(${it[2]})`], font: FONT, size: 24 })] }));
  else if (k === "FIG") {
    const buf = fs.readFileSync(path.join(GBR, it[1]));
    const w = Math.round(Math.min(it[2], 15) / 15 * 560), h = Math.round(w * buf.readUInt32BE(20) / buf.readUInt32BE(16));
    fig += 1;
    children.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 80, after: 40 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h }, altText: { title: it[3], description: it[3], name: it[1] } })] }));
    children.push(C(it[3], { size: 22, after: 120 }));
  } else if (k === "TAB") {
    const [, cap, head, rows, wcm] = it;
    const tot = wcm.reduce((a, b) => a + b, 0);
    const ws = wcm.map((x) => Math.round((x / tot) * TW)); ws[ws.length - 1] += TW - ws.reduce((a, b) => a + b, 0);
    const cell = (t, i, top, bot, b) => new TableCell({ width: { size: ws[i], type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
      borders: { top: top ? B : N, bottom: bot ? B : N, left: N, right: N }, margins: { left: 60, right: 60 },
      children: [new Paragraph({ alignment: i ? AlignmentType.CENTER : AlignmentType.LEFT, children: [new TextRun({ text: t, font: FONT, size: 20, bold: b })] })] });
    children.push(C(cap, { keepNext: true, after: 60 }));
    children.push(new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: ws, rows: [
      new TableRow({ tableHeader: true, children: head.map((h, i) => cell(h, i, true, true, true)) }),
      ...rows.map((r, ri) => new TableRow({ children: r.map((c, i) => cell(c, i, false, ri === rows.length - 1, false)) }))] }));
    children.push(new Paragraph({ children: [], spacing: { after: 80 } }));
  }
}
children.push(P("**DAFTAR PUSTAKA**", { first: false, keepNext: true, after: 60 }));
A.pustaka.forEach((r, i) => children.push(new Paragraph({ alignment: AlignmentType.LEFT, indent: { left: 567, hanging: 567 }, spacing: { after: 60 },
  children: [new TextRun({ text: `[${i + 1}]\t`, font: FONT, size: 22 }), ...runs(r, { size: 22 })], tabStops: [{ type: TabStopType.LEFT, position: 567 }] })));
children.push(new Paragraph({ children: [new TextRun("SISIP_L8_SELESAI")] }));
const doc = new Document({ sections: [{ children }] });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[3], b); console.log("ditulis", process.argv[3], "| gambar", fig); });
