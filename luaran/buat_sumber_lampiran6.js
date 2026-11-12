// Sumber "Lampiran 6. Daftar Perangkat Lunak dan Versi" untuk luaran/sisip_ke_laporan.py (operasi lampiran6).
// Versi dicek dari env conda mbkm-nlu (importlib.metadata) dan results/eval_dataset_MSI_20261112_095743.md (Ollama, digest model).
//   node luaran/buat_sumber_lampiran6.js <keluaran.docx>
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType, AlignmentType,
  HeadingLevel, VerticalAlign } = require("docx");
const FONT = "Times New Roman";
const TW = 11906 - 4 * 567 - 3 * 567;
const B = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: o.size || 20, bold: o.bold, italics: o.italics });
const ROWS = [
  ["Lingkungan", "Python (conda env mbkm-nlu)", "3.11.18", "Bahasa pemrograman seluruh sistem"],
  ["Akuisisi audio", "sounddevice", "0.5.6", "Perekaman mikrofon (WASAPI)"],
  ["", "soundfile", "0.14.0", "Baca/tulis berkas WAV"],
  ["", "soxr", "1.1.0", "Resampling 48 kHz → 16 kHz"],
  ["VAD", "silero-vad", "6.2.3", "Model deteksi aktivitas suara"],
  ["", "ONNX Runtime", "1.31.0", "Inferensi model VAD (ONNX)"],
  ["ASR", "faster-whisper", "1.2.1", "Whisper base (implementasi terpilih)"],
  ["", "CTranslate2", "4.8.2", "Mesin inferensi faster-whisper (float16 GPU, int8 CPU)"],
  ["", "openai-whisper", "20250625", "Implementasi pembanding"],
  ["NLU – LLM", "Ollama", "0.30.6", "Server LLM lokal (HTTP API, structured output)"],
  ["", "Qwen2.5 1.5B (qwen2.5:1.5b)", "Q4_K_M, digest 65ec06548149", "Model NLU utama"],
  ["", "requests; jsonschema", "2.34.2; 4.26.0", "Pemanggilan API; validasi skema JSON"],
  ["NLU – IndoBERT", "PyTorch (CUDA 12.6)", "2.14.1", "Pelatihan dan inferensi IndoBERT"],
  ["", "transformers", "5.22.2", "Model indobenchmark/indobert-base-p1"],
  ["Evaluasi", "jiwer", "4.0.0", "Word Error Rate"],
  ["", "scikit-learn", "1.9.1", "Precision, recall, F1, confusion matrix"],
  ["", "SciPy", "1.17.1", "Uji McNemar eksak (binomtest)"],
  ["", "NumPy", "2.4.6", "Komputasi numerik"],
  ["Antarmuka & konfigurasi", "rich; PyYAML", "15.0.0; 6.0.3", "CLI interaktif; berkas config.yaml"],
  ["Grafik", "matplotlib", "3.10.3", "Grafik hasil evaluasi"],
];
const W = [2600, 3000, 2300, TW - 7900];
const cell = (t, i, head) => new TableCell({ borders: { top: B, bottom: B, left: B, right: B }, width: { size: W[i], type: WidthType.DXA },
  verticalAlign: VerticalAlign.CENTER, shading: head ? { fill: "D9D9D9", type: ShadingType.CLEAR, color: "auto" } : undefined,
  margins: { top: 40, bottom: 40, left: 80, right: 80 },
  children: [new Paragraph({ alignment: head ? AlignmentType.CENTER : AlignmentType.LEFT, children: [run(t, { bold: head })] })] });
const doc = new Document({ sections: [{ children: [
  new Paragraph({ children: [new TextRun("SISIP_L6_MULAI")] }),
  new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 120, after: 80 }, children: [run("Lampiran 6. Daftar Perangkat Lunak dan Versi", { bold: true, size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 }, children: [run("Seluruh pengujian dijalankan dengan versi perangkat lunak berikut (terkunci di environment.yml repositori) sehingga hasil dapat direproduksi.", { size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 }, children: [run("Tabel L.1. Perangkat Lunak, Versi, dan Fungsinya", { bold: true, size: 24 })] }),
  new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: W, rows: [
    new TableRow({ tableHeader: true, children: ["Komponen", "Pustaka / alat", "Versi", "Fungsi"].map((h, i) => cell(h, i, true)) }),
    ...ROWS.map((r) => new TableRow({ children: r.map((c, i) => cell(c, i, false)) })),
  ] }),
  new Paragraph({ children: [new TextRun("SISIP_L6_SELESAI")] }),
] }] });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[2], b); console.log("ditulis", process.argv[2]); });
