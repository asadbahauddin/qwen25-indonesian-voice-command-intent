// Slide monev LPPM (gaya teknik & infografis). Angka dibaca dari results/ (bukan diketik).
//   NODE_PATH=<folder node_modules berisi pptxgenjs> node luaran/buat_slide_monev.js <apply_theme.js>
// Keluaran: luaran/slide/Monev_LPPM_MBKM_Asad.pptx
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.argv[2]);

const ROOT = path.join(__dirname, "..");
const EV = JSON.parse(fs.readFileSync(path.join(ROOT, "results/eval_dataset_MSI_20261112_095743.json"), "utf-8"));
const AN = JSON.parse(fs.readFileSync(path.join(ROOT, "results/analisis_dataset_MSI_20261112_104423.json"), "utf-8"));
const LOGO = (f) => path.join(__dirname, "logo", f);
const OUT = process.env.OUT_PPTX || path.join(__dirname, "slide", "Monev_LPPM_MBKM_Asad.pptx");

const id = (x, d = 1) => x.toFixed(d).replace(".", ",");
const acc = (dev, mk, m, k = "intent_acc", sub = "semua") => EV.akurasi[`${dev}/${mk}/${m}`][sub][k] * 100;
const lat = (dev, k) => EV.latency[`${dev}/vad/qwen`][k];
const wer = (mk) => EV.wer[`gpu/${mk}`].semua.wer * 100;
const recallComb = AN.per_intent["gpu/teks"].qwen.combined_command.r;

// ---------- tema ----------
const THEME = {
  name: "MBKM Teknik Data",
  headFontFace: "Segoe UI Semibold",
  bodyFontFace: "Segoe UI",
  colors: {
    dk1: "14213D", lt1: "FFFFFF", dk2: "0B1E33", lt2: "EEF3F8",
    accent1: "F5B700", accent2: "1F6FB2", accent3: "8A94A6", accent4: "4FC3F7", accent5: "2E9E6B", accent6: "D9534F",
    hlink: "1F6FB2", folHlink: "6B4FA0",
  },
};
const HEX = THEME.colors;
const MONO = "Consolas";
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13,33 x 7,5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Monev LPPM — Evaluasi Qwen2.5 untuk Intent Perintah Robot";
pres.author = "As'ad Bahauddin Ahmad";
const C = pres.SchemeColor;
// warna metode (tetap di seluruh dek): Qwen = kuning (metode utama), rule = abu, IndoBERT = biru
const MCOL = [HEX.accent1, HEX.accent3, HEX.accent2];
const METODE = ["Qwen2.5 1.5B", "Rule-based", "IndoBERT"];
const MKEY = ["qwen", "rule", "indobert"];

// ---------- layout ----------
pres.defineSlideMaster({
  title: "JUDUL", background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.35, w: 11.9, h: 1.9, fontFace: THEME.headFontFace, fontSize: 34, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "ISI", background: { color: HEX.lt1 },
  margin: [0.5, 0.6, 0.7, 0.6],
  objects: [
    { placeholder: { options: { name: "tag", type: "body", x: 0.6, y: 0.32, w: 8, h: 0.3, fontFace: MONO, fontSize: 11, color: C.accent2, bold: true, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.62, w: 10.4, h: 0.75, fontFace: THEME.headFontFace, fontSize: 30, color: C.text1, valign: "top", align: "left", margin: 0 }, text: "" } },
    { image: { x: 11.35, y: 0.3, w: 1.42, h: 0.774, path: LOGO("mekatronika.png"), altText: "Logo Teknik Mekatronika UTM" } },
    { text: { text: "Monev LPPM · Asistensi Hibah Penelitian (MBKM Riset) 2026", options: { x: 0.6, y: 7.05, w: 8, h: 0.3, fontFace: MONO, fontSize: 9, color: C.accent3, margin: 0 } } },
  ],
  slideNumber: { x: 12.25, y: 7.05, w: 0.5, h: 0.3, fontFace: MONO, fontSize: 9, color: C.accent3, align: "right" },
});
pres.defineSlideMaster({
  title: "GELAP", background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: "tag", type: "body", x: 0.7, y: 0.45, w: 8, h: 0.3, fontFace: MONO, fontSize: 11, color: C.accent1, bold: true, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 0.78, w: 11.9, h: 0.8, fontFace: THEME.headFontFace, fontSize: 30, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    { image: { x: 0.7, y: 6.72, w: 2.84, h: 0.5, path: LOGO("lppm_utm.png"), altText: "Logo LPPM Universitas Trunojoyo Madura" } },
  ],
  slideNumber: { x: 12.25, y: 7.05, w: 0.5, h: 0.3, fontFace: MONO, fontSize: 9, color: C.accent4, align: "right" },
});

// ---------- komponen ----------
let nObj = 0;
const nm = (s) => `${s}_${++nObj}`;
const shadow = () => ({ type: "outer", color: "0B1E33", opacity: 0.12, blur: 6, offset: 2, angle: 90 });
function kartu(s, x, y, w, h, fill = C.background2, o = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: fill, width: 0 }, rectRadius: 0.08, shadow: o.shadow ? shadow() : undefined, objectName: nm("kartu") });
}
function teks(s, t, o) { s.addText(t, { isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top", objectName: nm("teks"), ...o }); }
function angka(s, x, y, w, nilai, label, warna = C.text2) {
  kartu(s, x, y, w, 1.45, C.background2);
  teks(s, nilai, { x: x + 0.25, y: y + 0.18, w: w - 0.5, h: 0.7, fontFace: THEME.headFontFace, fontSize: 36, color: warna, valign: "middle" });
  teks(s, label, { x: x + 0.25, y: y + 0.9, w: w - 0.5, h: 0.45, fontSize: 12, color: C.text1 });
}
function nomor(s, x, y, t, fill = C.accent1, warna = C.text2) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 0.5, h: 0.5, fill: { color: fill }, line: { color: fill, width: 0 }, rectRadius: 0.1, objectName: nm("nomor") });
  teks(s, t, { x, y, w: 0.5, h: 0.5, fontFace: MONO, fontSize: 14, bold: true, color: warna, align: "center", valign: "middle" });
}
const sumber = (s, t, dark = false) => teks(s, t, { x: 0.6, y: 6.7, w: 10.5, h: 0.3, fontFace: MONO, fontSize: 9, color: dark ? C.accent4 : C.accent3 });
const CHART = {
  catAxisLabelColor: "14213D", valAxisLabelColor: "5B6470", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  catAxisLabelFontSize: 12, valAxisLabelFontSize: 10, dataLabelFontFace: "+mn-lt", dataLabelFontSize: 10, dataLabelColor: "14213D",
  valGridLine: { color: "DDE3EA", size: 0.75 }, catGridLine: { style: "none" }, legendFontFace: "+mn-lt", legendFontSize: 11, legendColor: "14213D",
  titleFontFace: "+mj-lt", titleFontSize: 14, titleColor: "14213D",
};

// ========== 1. Judul ==========
pres.addSection({ title: "Pembuka" });
let s = pres.addSlide({ masterName: "JUDUL", sectionTitle: "Pembuka" });
s.addImage({ path: LOGO("lppm_utm.png"), x: 0.7, y: 0.55, w: 3.98, h: 0.7, altText: "Logo LPPM Universitas Trunojoyo Madura", objectName: nm("logo") });
kartu(s, 8.05, 0.4, 4.6, 1.1, C.background1);
s.addImage({ path: LOGO("utm.png"), x: 8.25, y: 0.55, w: 0.76, h: 0.75, altText: "Logo Universitas Trunojoyo Madura", objectName: nm("logo") });
s.addImage({ path: LOGO("kampus_merdeka.png"), x: 9.2, y: 0.58, w: 1.32, h: 0.695, altText: "Logo Kampus Merdeka (MBKM)", objectName: nm("logo") });
s.addImage({ path: LOGO("mekatronika.png"), x: 10.75, y: 0.5, w: 1.72, h: 0.94, altText: "Logo Teknik Mekatronika UTM", objectName: nm("logo") });
teks(s, "MONITORING & EVALUASI  ·  ASISTENSI HIBAH PENELITIAN (MBKM RISET) 2026", { x: 0.7, y: 1.85, w: 11.5, h: 0.35, fontFace: MONO, fontSize: 13, bold: true, color: C.accent1 });
s.addText("Evaluasi Large Language Model Qwen2.5 untuk Ekstraksi Intent Perintah Kalimat Bebas Bahasa Indonesia pada Robot", { placeholder: "title" });
s.addShape(pres.shapes.LINE, { x: 0.7, y: 4.55, w: 11.9, h: 0, line: { color: "2A4466", width: 1 }, objectName: nm("garis") });
teks(s, [
  { text: "As'ad Bahauddin Ahmad", options: { bold: true, fontSize: 18, color: C.background1, breakLine: true } },
  { text: "Mahasiswa · Teknik Mekatronika · NIM 230491100034", options: { fontSize: 13, color: C.accent4 } },
], { x: 0.7, y: 4.8, w: 6, h: 0.9 });
teks(s, [
  { text: "Ir. Vivi Tri Widyaningrum, S.Kom., M.T.", options: { bold: true, fontSize: 18, color: C.background1, breakLine: true } },
  { text: "Dosen pembimbing · Laboratorium Sistem Otomasi", options: { fontSize: 13, color: C.accent4 } },
], { x: 6.9, y: 4.8, w: 5.7, h: 0.9 });
teks(s, "Program Studi Teknik Mekatronika · Fakultas Teknik · Universitas Trunojoyo Madura", { x: 0.7, y: 6.6, w: 11.9, h: 0.35, fontSize: 12, color: C.accent3 });
s.addNotes("Pembuka: judul penelitian, mahasiswa, dosen pembimbing, program Asistensi Hibah Penelitian (MBKM Riset) LPPM UTM 2026.");

// ========== 2. Ringkasan capaian ==========
pres.addSection({ title: "Ringkasan" });
s = pres.addSlide({ masterName: "ISI", sectionTitle: "Ringkasan" });
s.addText("00 / RINGKASAN CAPAIAN", { placeholder: "tag" });
s.addText("Pengujian selesai; luaran sedang difinalkan", { placeholder: "title" });
angka(s, 0.6, 1.7, 2.85, "162", "ujaran kalimat bebas dari 3 responden (set uji)");
angka(s, 3.65, 1.7, 2.85, "3", "metode NLU dibandingkan pada antarmuka yang sama");
angka(s, 6.7, 1.7, 2.85, `${id(lat("gpu", "t_respons").mean, 2)} s`, "waktu respons pipeline suara → JSON (laptop GPU)");
angka(s, 9.75, 1.7, 2.98, `${id(acc("gpu", "teks", "indobert"))}%`, "intent accuracy terbaik (IndoBERT, teks)", C.accent2);
// progres fase
teks(s, "PROGRES FASE", { x: 0.6, y: 3.5, w: 4, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: C.accent2 });
const fase = [["F0–F6", "Lingkungan, mikrofon, VAD, Whisper, NLU, pipeline, uji pilot", "Selesai", C.accent5],
  ["F7", "Deployment Raspberry Pi 5", "Diganti laptop", C.accent6],
  ["F8–F9", "Perekaman 162 ujaran, pelabelan, evaluasi set uji", "Selesai", C.accent5],
  ["F10", "Laporan, artikel JoTI, HKI, poster", "Finalisasi", C.accent1]];
fase.forEach(([f, d, st, col], i) => {
  const y = 3.9 + i * 0.68;
  kartu(s, 0.6, y, 12.13, 0.56, C.background2);
  teks(s, f, { x: 0.8, y, w: 1.2, h: 0.56, fontFace: MONO, fontSize: 14, bold: true, color: C.text2, valign: "middle" });
  teks(s, d, { x: 2.1, y, w: 7.8, h: 0.56, fontSize: 14, valign: "middle" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 10.25, y: y + 0.11, w: 2.3, h: 0.34, fill: { color: col }, line: { color: col, width: 0 }, rectRadius: 0.17, objectName: nm("status") });
  teks(s, st, { x: 10.25, y: y + 0.11, w: 2.3, h: 0.34, fontSize: 12, bold: true, color: col === C.accent1 ? C.text2 : C.background1, align: "center", valign: "middle" });
});
s.addNotes("Pengujian (F0–F9) sudah selesai pada set uji 162 ujaran. Deployment RPi 5 dibatalkan dan diganti laptop karena RPi 5 tidak dapat booting. Luaran sedang difinalkan.");

// ========== 3. Masalah & tujuan ==========
pres.addSection({ title: "Latar & Metode" });
s = pres.addSlide({ masterName: "ISI", sectionTitle: "Latar & Metode" });
s.addText("01 / LATAR BELAKANG", { placeholder: "tag" });
s.addText("Robot perlu memahami kalimat bebas, offline", { placeholder: "title" });
kartu(s, 0.6, 1.7, 4.6, 4.85, C.text2);
teks(s, "MASALAH", { x: 0.9, y: 1.95, w: 4, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: C.accent1 });
teks(s, "Antarmuka suara konvensional hanya mengenali perintah berstruktur tetap. LLM praterlatih menjanjikan pemahaman kalimat bebas, tetapi evaluasinya untuk Bahasa Indonesia secara offline masih jarang.", { x: 0.9, y: 2.35, w: 4.0, h: 2.6, fontSize: 16, color: C.background1 });
teks(s, "Keluaran = JSON perintah robot (intent + entitas) sebagai antarmuka ke pengendali; penggerakan robot fisik di luar ruang lingkup.", { x: 0.9, y: 5.0, w: 4.0, h: 1.3, fontSize: 13, color: C.accent4 });
const rm = [["RM1", "Seberapa akurat Qwen2.5 1.5B mengekstrak intent dan entitas dari perintah kalimat bebas?"],
  ["RM2", "Berapa latency end-to-end dari suara hingga JSON perintah robot secara offline?"],
  ["RM3", "Bagaimana Qwen2.5 dibanding rule-based dan IndoBERT pada tiga tingkat formalitas?"]];
rm.forEach(([k, t], i) => {
  const y = 1.7 + i * 1.65;
  kartu(s, 5.5, y, 7.23, 1.45, C.background2);
  nomor(s, 5.75, y + 0.47, String(i + 1));
  teks(s, k, { x: 6.5, y: y + 0.22, w: 6, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: C.accent2 });
  teks(s, t, { x: 6.5, y: y + 0.52, w: 6.0, h: 0.8, fontSize: 15 });
});
s.addNotes("Latar belakang dan tiga rumusan masalah (akurasi, latency, perbandingan pada formalitas).");

// ========== 4. Pipeline ==========
s = pres.addSlide({ masterName: "ISI", sectionTitle: "Latar & Metode" });
s.addText("02 / METODE", { placeholder: "tag" });
s.addText("Pipeline offline: suara menjadi JSON perintah robot", { placeholder: "title" });
const blok = [["Mikrofon", "lavalier USB\n48 kHz → 16 kHz mono"], ["Silero VAD", "ONNX · threshold 0,5\njeda 1,2 s · pre-roll 300 ms"],
  ["Whisper base", "faster-whisper · beam 5\nprompt domain lab"], ["NLU", "Qwen2.5\nRule-based\nIndoBERT"], ["JSON", "intent + room, object,\nperson, document, steps"]];
const bw = 2.1, gap = 0.4, x0 = 0.6;
blok.forEach(([j, d], i) => {
  const x = x0 + i * (bw + gap), utama = i === 3;
  kartu(s, x, 1.85, bw, 1.9, utama ? C.text2 : C.background2);
  teks(s, String(i + 1).padStart(2, "0"), { x: x + 0.2, y: 2.0, w: 1, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: utama ? C.accent1 : C.accent2 });
  teks(s, j, { x: x + 0.2, y: 2.3, w: bw - 0.4, h: 0.45, fontFace: THEME.headFontFace, fontSize: 18, color: utama ? C.background1 : C.text1 });
  teks(s, d, { x: x + 0.2, y: 2.82, w: bw - 0.35, h: 0.85, fontSize: 12, color: utama ? C.accent4 : C.text1 });
  if (i < blok.length - 1) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + 0.08, y: 2.66, w: 0.24, h: 0.28, fill: { color: C.accent2 }, line: { color: C.accent2, width: 0 }, objectName: nm("panah") });
});
const nlu = [["Qwen2.5 1.5B (metode utama)", "Q4_K_M via Ollama · prompt few-shot · structured output JSON Schema · temperature 0, seed 42", C.accent1],
  ["Rule-based (baseline bawah)", "kamus kata kunci per intent + kamus entitas bersama · pemecahan klausa pada kata penghubung", C.accent3],
  ["IndoBERT (baseline supervised)", "indobert-base-p1 di-fine-tune 300 kalimat sintetis (50/intent) · klasifikasi intent per klausa", C.accent2]];
nlu.forEach(([j, d, col], i) => {
  const y = 4.15 + i * 0.82;
  s.addShape(pres.shapes.OVAL, { x: 0.65, y: y + 0.17, w: 0.28, h: 0.28, fill: { color: col }, line: { color: col, width: 0 }, objectName: nm("titik") });
  teks(s, j, { x: 1.15, y, w: 3.6, h: 0.62, fontSize: 15, bold: true, valign: "middle" });
  teks(s, d, { x: 4.8, y, w: 7.9, h: 0.62, fontSize: 13, valign: "middle" });
});
s.addNotes("Semua tahap berjalan offline di laptop. Ketiga metode NLU memakai antarmuka predict(text) -> (json, info) yang sama sehingga dapat dibandingkan langsung.");

// ========== 5. Desain eksperimen ==========
s = pres.addSlide({ masterName: "ISI", sectionTitle: "Latar & Metode" });
s.addText("03 / DESAIN EKSPERIMEN", { placeholder: "tag" });
s.addText("Data uji dipisah ketat dari data pengembangan", { placeholder: "title" });
const dset = [["Set pilot", "36", "kalimat sintetis; set pengembangan (prompt, skema, backend Whisper)"],
  ["Data latih IndoBERT", "300", "kalimat templat, 50 per intent; dicek tanpa kebocoran"],
  ["Set uji responden", String(EV.n_item), "ujaran: 3 responden × 54 kartu skenario; tidak dipakai untuk pengembangan"]];
dset.forEach(([j, n, d], i) => {
  const x = 0.6 + i * 4.11;
  kartu(s, x, 1.7, 3.9, 2.25, i === 2 ? C.text2 : C.background2);
  teks(s, j.toUpperCase(), { x: x + 0.25, y: 1.88, w: 3.4, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: i === 2 ? C.accent1 : C.accent2 });
  teks(s, n, { x: x + 0.25, y: 2.2, w: 3.4, h: 0.75, fontFace: THEME.headFontFace, fontSize: 40, color: i === 2 ? C.background1 : C.text2 });
  teks(s, d, { x: x + 0.25, y: 3.0, w: 3.45, h: 0.85, fontSize: 13, color: i === 2 ? C.accent4 : C.text1 });
});
teks(s, "6 INTENT × 3 FORMALITAS", { x: 0.6, y: 4.25, w: 6, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: C.accent2 });
const intents = ["navigate_room", "navigate_object", "find_person", "deliver_document", "combined_command", "general_command"];
intents.forEach((it, i) => {
  const x = 0.6 + (i % 3) * 2.1, y = 4.65 + Math.floor(i / 3) * 0.55;
  kartu(s, x, y, 1.95, 0.42, C.background2);
  teks(s, it, { x: x + 0.1, y, w: 1.8, h: 0.42, fontFace: MONO, fontSize: 11, align: "center", valign: "middle", color: C.text2 });
});
teks(s, "27 ujaran per intent · formal / semi-formal / informal 54 ujaran masing-masing", { x: 0.6, y: 5.85, w: 6.2, h: 0.5, fontSize: 12, color: C.text1 });
kartu(s, 7.0, 4.25, 5.73, 2.3, C.background2);
teks(s, "METRIK", { x: 7.25, y: 4.4, w: 4, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: C.accent2 });
teks(s, [
  { text: "ASR: Word Error Rate (jiwer)", options: { bullet: true, breakLine: true } },
  { text: "NLU: intent accuracy, exact match, F1, confusion matrix", options: { bullet: true, breakLine: true } },
  { text: "Uji McNemar untuk beda antarmetode", options: { bullet: true, breakLine: true } },
  { text: "Latency per tahap: rata-rata ± SD, n = 162", options: { bullet: true } },
], { x: 7.25, y: 4.75, w: 5.3, h: 1.7, fontSize: 14, paraSpaceAfter: 4 });
s.addNotes("Pemisahan data mencegah kebocoran: pilot untuk pengembangan, data latih IndoBERT terpisah, set uji responden hanya untuk evaluasi akhir. Ketiga metode diuji pada teks acuan dan pada transkrip Whisper.");

// ========== 6. Akurasi ==========
pres.addSection({ title: "Hasil" });
s = pres.addSlide({ masterName: "ISI", sectionTitle: "Hasil" });
s.addText("04 / HASIL AKURASI", { placeholder: "tag" });
s.addText("IndoBERT terakurat, di teks maupun suara", { placeholder: "title" });
const kat = ["Teks acuan", "Pipeline suara"];
const ser = (k) => MKEY.map((m, i) => ({ name: METODE[i], labels: kat, values: ["teks", "vad"].map((mk) => +acc("gpu", mk, m, k).toFixed(1)) }));
const optBar = (judul) => ({
  ...CHART, barDir: "col", barGrouping: "clustered", chartColors: MCOL, showValue: true, dataLabelPosition: "outEnd",
  dataLabelFormatCode: "0.0", valAxisMinVal: 0, valAxisMaxVal: 110, valAxisMajorUnit: 20, showTitle: true, title: judul,
  showLegend: true, legendPos: "b", barGapWidthPct: 60,
});
s.addChart(pres.charts.BAR, ser("intent_acc"), { x: 0.6, y: 1.6, w: 6.0, h: 4.6, ...optBar("Intent Accuracy (%)"), objectName: nm("grafik_intent") });
s.addChart(pres.charts.BAR, ser("exact_match"), { x: 6.73, y: 1.6, w: 6.0, h: 4.6, ...optBar("Exact Match (%)"), objectName: nm("grafik_em") });
sumber(s, `Laptop GPU, n = ${EV.n_item}. Pipeline suara = segmen VAD → Whisper base (WER ${id(wer("vad"))}%). Sumber: results/eval_dataset_MSI_20261112_095743.json`);
s.addNotes("Pada teks acuan IndoBERT tertinggi untuk intent, rule-based dan IndoBERT setara untuk exact match. Pada pipeline suara semua metode turun karena galat transkripsi Whisper base. McNemar: IndoBERT > Qwen2.5 untuk intent, p < 0,001 pada semua masukan.");

// ========== 7. Formalitas ==========
s = pres.addSlide({ masterName: "ISI", sectionTitle: "Hasil" });
s.addText("05 / FORMALITAS", { placeholder: "tag" });
s.addText("Qwen2.5 tidak lebih unggul pada kalimat informal", { placeholder: "title" });
const fk = ["formal", "semi-formal", "informal"];
const serF = MKEY.map((m, i) => ({ name: METODE[i], labels: ["Formal", "Semi-formal", "Informal"], values: fk.map((f) => +acc("gpu", "teks", m, "intent_acc", `formality=${f}`).toFixed(1)) }));
s.addChart(pres.charts.BAR, serF, { x: 0.6, y: 1.6, w: 7.6, h: 4.9, ...optBar("Intent Accuracy per formalitas — teks acuan (%)"), objectName: nm("grafik_formalitas") });
kartu(s, 8.5, 1.6, 4.23, 4.9, C.text2);
teks(s, "TEMUAN", { x: 8.8, y: 1.85, w: 3.6, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: C.accent1 });
teks(s, `${id(recallComb, 2)}`, { x: 8.8, y: 2.2, w: 3.6, h: 0.9, fontFace: THEME.headFontFace, fontSize: 48, color: C.accent1 });
teks(s, "recall Qwen2.5 untuk combined_command (teks): perintah majemuk hampir selalu dibaca sebagai perintah tunggal.", { x: 8.8, y: 3.1, w: 3.65, h: 1.3, fontSize: 14, color: C.background1 });
teks(s, "Kelemahan ini, bukan gaya bahasa, yang paling menurunkan akurasi Qwen2.5. Saran: pemecahan klausa sebelum LLM.", { x: 8.8, y: 4.55, w: 3.65, h: 1.6, fontSize: 13, color: C.accent4 });
sumber(s, "Laptop GPU, n = 54 per formalitas. Sumber: results/eval_dataset_… dan results/analisis_dataset_MSI_20261112_104423.json");
s.addNotes("Hipotesis H2 (Qwen lebih robust pada informal) tidak terdukung: IndoBERT tertinggi di ketiga formalitas.");

// ========== 8. Latency ==========
s = pres.addSlide({ masterName: "ISI", sectionTitle: "Hasil" });
s.addText("06 / LATENCY", { placeholder: "tag" });
s.addText("Respons di bawah target 15 s, juga tanpa GPU", { placeholder: "title" });
const tahap = [["VAD", "t_vad"], ["Whisper", "t_asr"], ["Qwen2.5", "t_nlu"]];
const serL = tahap.map(([n, k]) => ({ name: n, labels: ["Laptop GPU", "Laptop CPU"], values: ["gpu", "cpu"].map((d) => +lat(d, k).mean.toFixed(2)) }));
s.addChart(pres.charts.BAR, serL, {
  x: 0.6, y: 1.6, w: 7.6, h: 4.9, ...CHART, barDir: "bar", barGrouping: "stacked", chartColors: [HEX.accent4, HEX.accent2, HEX.accent1],
  showValue: true, dataLabelPosition: "ctr", dataLabelFormatCode: '[<0.1]"";0.00', dataLabelColor: "0B1E33", showTitle: true, title: "Waktu komputasi rata-rata per tahap (s)",
  showLegend: true, legendPos: "b", valAxisMinVal: 0, barGapWidthPct: 50, objectName: nm("grafik_latency"),
});
const rG = lat("gpu", "t_respons"), rC = lat("cpu", "t_respons");
angka(s, 8.5, 1.6, 4.23, `${id(rG.mean, 2)} ± ${id(rG.sd, 2)} s`, "waktu respons laptop GPU (RTX 2050)");
angka(s, 8.5, 3.25, 4.23, `${id(rC.mean, 2)} ± ${id(rC.sd, 2)} s`, "waktu respons laptop CPU (tanpa GPU)");
kartu(s, 8.5, 4.9, 4.23, 1.6, C.text2);
teks(s, "H3 · TARGET < 15 s", { x: 8.75, y: 5.05, w: 3.8, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: C.accent1 });
teks(s, "Tercapai di GPU untuk semua ujaran. Di CPU sebagian kecil ujaran melewati 15 s saat RAM penuh (swap).", { x: 8.75, y: 5.4, w: 3.8, h: 1.0, fontSize: 13, color: C.background1 });
sumber(s, "Pipeline Qwen2.5, n = 162. Waktu respons = komputasi + jeda tunggu akhir ujaran VAD. Sumber: results/eval_dataset_MSI_20261112_095743.json");
s.addNotes("Qwen2.5 mendominasi waktu komputasi. Whisper base di CPU (int8) jauh lebih lambat dari GPU. Platform yang diuji laptop, bukan Raspberry Pi 5.");

// ========== 9. Hipotesis ==========
s = pres.addSlide({ masterName: "ISI", sectionTitle: "Hasil" });
s.addText("07 / HIPOTESIS", { placeholder: "tag" });
s.addText("Satu dari tiga hipotesis tercapai (platform laptop)", { placeholder: "title" });
const fs2 = (mk) => (acc("gpu", mk, "qwen", "intent_acc", "formality=formal") + acc("gpu", mk, "qwen", "intent_acc", "formality=semi-formal")) / 2; // n = 54 + 54
const hip = [
  ["H1", "Akurasi Qwen2.5 > 80% (formal & semi-formal)", `Formal + semi-formal: teks ${id(fs2("teks"), 2)}%, pipeline suara ${id(fs2("vad"), 2)}%`, "Tidak tercapai", C.accent6],
  ["H2", "Qwen2.5 lebih robust pada kalimat informal", `IndoBERT tertinggi di semua formalitas; McNemar p < 0,001`, "Tidak terdukung", C.accent6],
  ["H3", "Latency end-to-end < 15 s", `GPU ${id(rG.mean, 2)} s; CPU ${id(rC.mean, 2)} s rata-rata`, "Tercapai", C.accent5]];
hip.forEach(([k, h, b, st, col], i) => {
  const y = 1.75 + i * 1.55;
  kartu(s, 0.6, y, 12.13, 1.35, C.background2);
  nomor(s, 0.85, y + 0.42, k, C.text2, C.accent1);
  teks(s, h, { x: 1.65, y: y + 0.2, w: 7.5, h: 0.45, fontSize: 18, bold: true });
  teks(s, b, { x: 1.65, y: y + 0.7, w: 7.8, h: 0.45, fontSize: 14, color: C.text1 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.95, y: y + 0.45, w: 2.55, h: 0.45, fill: { color: col }, line: { color: col, width: 0 }, rectRadius: 0.2, objectName: nm("status") });
  teks(s, st, { x: 9.95, y: y + 0.45, w: 2.55, h: 0.45, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle" });
});
sumber(s, "Proposal menyebut RPi 5; dijawab di laptop offline (RPi 5 gagal booting). Angka laptop bukan kinerja RPi 5.");
s.addNotes("H1 diuji pada gabungan formal dan semi-formal. Hasil negatif tetap temuan: model 1.5B belum cukup untuk perintah majemuk tanpa pemecahan klausa.");

// ========== 10. Luaran ==========
pres.addSection({ title: "Luaran & Kendala" });
s = pres.addSlide({ masterName: "ISI", sectionTitle: "Luaran & Kendala" });
s.addText("08 / LUARAN", { placeholder: "tag" });
s.addText("Status luaran wajib dan tambahan", { placeholder: "title" });
const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 }, fontFace: MONO, fontSize: 12 } });
const st = (t, col) => ({ text: t, options: { bold: true, color: col } });
s.addTable([
  [hdr("Luaran"), hdr("Jenis"), hdr("Status")],
  ["Laporan akhir", "Wajib", st("Draf lengkap (47 hlm, Lampiran 1–9)", C.accent5)],
  ["Artikel ilmiah — Journal of Technology and Informatics (JoTI)", "Wajib", st("Draf selesai; finalisasi bersama pembimbing", C.accent1)],
  ["Hak cipta program komputer (e-HKI UTM)", "Wajib", st("Diajukan 12 Nov 2026; menunggu konfirmasi LPPM", C.accent1)],
  ["Poster ilmiah A1", "Tambahan", st("Selesai", C.accent5)],
  ["Dataset 162 ujaran berlabel + data card", "Tambahan", st("Selesai; tidak dipublikasikan terbuka", C.accent5)],
], {
  x: 0.6, y: 1.7, w: 12.13, colW: [6.2, 1.7, 4.23], fontSize: 14, color: C.text1, fontFace: THEME.bodyFontFace,
  border: { type: "solid", pt: 0.75, color: "DDE3EA" }, fill: { color: HEX.lt1 }, rowH: 0.62, valign: "middle", margin: 0.1,
  objectName: nm("tabel_luaran"),
});
teks(s, "Kode program dipublikasikan di repositori GitHub publik (11 Nov 2026), dasar tanggal pengumuman HKI.", { x: 0.6, y: 5.75, w: 12, h: 0.4, fontSize: 13, color: C.text1 });
s.addNotes("Luaran wajib: laporan, artikel, HKI. Luaran tambahan: poster dan dataset dengan data card.");

// ========== 11. Kendala ==========
s = pres.addSlide({ masterName: "ISI", sectionTitle: "Luaran & Kendala" });
s.addText("09 / KENDALA & SOLUSI", { placeholder: "tag" });
s.addText("Kendala utama tertangani tanpa mengubah desain inti", { placeholder: "title" });
const kd = [["Raspberry Pi 5 tidak dapat booting", "Dicoba berulang kali dan microSD diganti; kendala terlama.", "Pengujian pada laptop offline (GPU dan CPU); RPi 5 jadi saran penelitian lanjutan."],
  ["RAM laptop 7,7 GB hampir penuh", "Lonjakan latency 20+ s saat swap di skenario CPU.", "Aplikasi lain ditutup saat evaluasi; pencilan dilaporkan apa adanya."],
  ["Perintah majemuk gagal di Qwen2.5", `Recall combined_command ${id(recallComb, 2)} (teks).`, "Dilaporkan sebagai temuan; saran pemecahan klausa sebelum LLM."]];
kd.forEach(([k, d, sol], i) => {
  const x = 0.6 + i * 4.11;
  kartu(s, x, 1.7, 3.9, 4.8, C.background2);
  nomor(s, x + 0.25, 1.95, String(i + 1), C.accent6, C.background1);
  teks(s, k, { x: x + 0.25, y: 2.6, w: 3.4, h: 0.9, fontSize: 17, bold: true });
  teks(s, d, { x: x + 0.25, y: 3.5, w: 3.4, h: 1.0, fontSize: 13 });
  teks(s, "SOLUSI", { x: x + 0.25, y: 4.6, w: 3.4, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: C.accent5 });
  teks(s, sol, { x: x + 0.25, y: 4.92, w: 3.4, h: 1.4, fontSize: 13 });
});
s.addNotes("Kendala dan solusinya. Penyimpangan platform dari proposal dijelaskan di BAB III laporan akhir.");

// ========== 12. Kesimpulan ==========
pres.addSection({ title: "Penutup" });
s = pres.addSlide({ masterName: "GELAP", sectionTitle: "Penutup" });
s.addText("10 / KESIMPULAN", { placeholder: "tag" });
s.addText("Pipeline offline layak; Qwen2.5 1.5B belum cukup akurat", { placeholder: "title" });
const kes = [
  ["RM1 · AKURASI", `${id(acc("gpu", "teks", "qwen"), 2)}%`, `intent accuracy Qwen2.5 pada teks; ${id(acc("gpu", "vad", "qwen"), 2)}% pada pipeline suara`,
    `Target 80% belum tercapai. Kelemahan utama: perintah majemuk (recall combined_command ${id(recallComb, 2)}).`],
  ["RM2 · LATENCY", `${id(rG.mean, 2)} s`, `waktu respons laptop GPU; ${id(rC.mean, 2)} s di laptop CPU`,
    "Seluruh pipeline berjalan offline dan di bawah target 15 s."],
  ["RM3 · PERBANDINGAN", `${id(acc("gpu", "teks", "indobert"), 2)}%`, "intent accuracy IndoBERT pada teks, tertinggi",
    `IndoBERT terbaik di semua formalitas; rule-based unggul exact match pada pipeline suara (${id(acc("gpu", "vad", "rule", "exact_match"), 2)}%). Qwen2.5 tidak lebih unggul pada kalimat informal.`],
];
kes.forEach(([tag, big, lbl, isi], i) => {
  const x = 0.7 + i * 4.05;
  kartu(s, x, 1.8, 3.85, 3.65, C.text1);
  teks(s, tag, { x: x + 0.3, y: 2.0, w: 3.3, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: C.accent1 });
  teks(s, big, { x: x + 0.3, y: 2.35, w: 3.3, h: 0.75, fontFace: THEME.headFontFace, fontSize: 36, color: C.accent1, valign: "middle" });
  teks(s, lbl, { x: x + 0.3, y: 3.15, w: 3.3, h: 0.6, fontSize: 12, color: C.accent4 });
  teks(s, isi, { x: x + 0.3, y: 3.85, w: 3.3, h: 1.45, fontSize: 14, color: C.background1 });
});
teks(s, "SARAN", { x: 0.7, y: 5.72, w: 1.2, h: 0.4, fontFace: MONO, fontSize: 12, bold: true, color: C.accent1, valign: "middle" });
teks(s, "Pemecahan klausa sebelum LLM  ·  LLM dan ASR lebih besar  ·  uji di Raspberry Pi 5  ·  integrasi ke robot",
  { x: 1.9, y: 5.72, w: 10.7, h: 0.4, fontSize: 14, color: C.background1, valign: "middle" });
kartu(s, 8.85, 6.5, 3.2, 0.72, C.background1);
s.addImage({ path: LOGO("utm.png"), x: 9.0, y: 6.56, w: 0.6, h: 0.594, altText: "Logo Universitas Trunojoyo Madura", objectName: nm("logo") });
s.addImage({ path: LOGO("kampus_merdeka.png"), x: 9.75, y: 6.58, w: 1.05, h: 0.553, altText: "Logo Kampus Merdeka (MBKM)", objectName: nm("logo") });
s.addImage({ path: LOGO("mekatronika.png"), x: 10.95, y: 6.57, w: 1.0, h: 0.545, altText: "Logo Teknik Mekatronika UTM", objectName: nm("logo") });
teks(s, "Terima kasih", { x: 4.2, y: 6.6, w: 4.3, h: 0.5, fontFace: THEME.headFontFace, fontSize: 20, color: C.background1, align: "center", valign: "middle" });
s.addNotes("Kesimpulan menjawab tiga rumusan masalah untuk platform laptop offline. Angka dibaca dari results/eval_dataset_MSI_20261112_095743.json dan results/analisis_dataset_MSI_20261112_104423.json. Tahap berikutnya: unggah dokumen e-HKI, finalisasi artikel JoTI, laporan akhir, seminar hasil 9–10 Des 2026.");

pres.writeFile({ fileName: OUT }).then(async () => { await applyTheme(OUT, THEME); console.log("ditulis", OUT); });
