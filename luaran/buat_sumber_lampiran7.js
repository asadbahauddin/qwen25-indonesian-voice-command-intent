// Sumber "Lampiran 7. Data Card dan Struktur Dataset" untuk luaran/sisip_ke_laporan.py (operasi lampiran7).
// Angka dibaca dari JSON hasil luaran/statistik_dataset.py (dihitung dari dataset/metadata.csv).
//   node luaran/buat_sumber_lampiran7.js <stat.json> <keluaran.docx>
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType, AlignmentType,
  HeadingLevel, VerticalAlign } = require("docx");
const S = JSON.parse(fs.readFileSync(process.argv[2], "utf-8"));
const FONT = "Times New Roman";
const TW = 11906 - 7 * 567;
const B = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const n2 = (x, d = 2) => x.toFixed(d).replace(".", ",");
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: o.size || 20, bold: o.bold, italics: o.italics });
const P = (t, o = {}) => new Paragraph({ alignment: o.align || AlignmentType.JUSTIFIED, spacing: { after: o.after ?? 100 },
  indent: o.first ? { firstLine: 720 } : undefined, children: [run(t, { size: 24, bold: o.bold })] });
const H3 = (t) => new Paragraph({ keepNext: true, spacing: { before: 120, after: 60 }, children: [run(t, { size: 24, bold: true })] });
const CAP = (t) => new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 }, children: [run(t, { size: 24, bold: true })] });
function T(head, rows, wcm, mono = []) {
  const tot = wcm.reduce((a, b) => a + b, 0);
  const w = wcm.map((x) => Math.round((x / tot) * TW)); w[w.length - 1] += TW - w.reduce((a, b) => a + b, 0);
  const cell = (t, i, h) => new TableCell({ borders: { top: B, bottom: B, left: B, right: B }, width: { size: w[i], type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER, shading: h ? { fill: "D9D9D9", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: [new Paragraph({ alignment: h ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({ text: t, bold: h, size: mono.includes(i) && !h ? 18 : 20, font: mono.includes(i) && !h ? "Consolas" : FONT })] })] });
  return new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: w, rows: [
    new TableRow({ tableHeader: true, children: head.map((h, i) => cell(h, i, true)) }),
    ...rows.map((r) => new TableRow({ children: r.map((c, i) => cell(c, i, false)) }))] });
}
const resp = S.responden.map((r) => `${r.penutur} (${r.jenis_kelamin === "P" ? "perempuan" : "laki-laki"}, ${r.usia} th, bahasa ibu ${r.bahasa_ibu[0].toUpperCase() + r.bahasa_ibu.slice(1)}${r.penutur === "R03" ? ", peneliti" : ""})`).join("; ");
const D = S.durasi, K = S.kata, E = S.entity_terisi;
const KOLOM = {
  penutur: "Kode responden (R01–R03), tanpa nama", mode: "Mode rekam (skenario = kalimat bebas)", urutan: "Urutan kartu saat perekaman (diacak per responden)",
  item_id: "Kode kartu skenario (S01–S54)", formality: "Gaya bahasa target: formal / semi-formal / informal", intent_target: "Intent target pada kartu",
  target_json: "Label target kartu (JSON); hanya acuan, bukan label akhir", teks_baca: "Kosong (tidak membaca kalimat)", tujuan: "Teks situasi pada kartu skenario",
  wav: "Lokasi berkas audio relatif (R0x/R0x_Syy.wav)", durasi_s: "Durasi rekaman (detik)", peak_dbfs: "Puncak sinyal (dBFS)", rms_dbfs: "Rata-rata energi (dBFS)",
  clip_native: "Jumlah sampel clipping pada sinyal native 48 kHz", take: "Nomor pengambilan (rekam ulang)", waktu: "Waktu perekaman",
  host: "Nama komputer perekam", perangkat: "Nama perangkat mikrofon", hostapi: "API audio (Windows WASAPI)", sr_native: "Sample rate asli perangkat (48 kHz)",
  transkrip: "Transkrip ground-truth hasil koreksi manual", label_final_json: "Label akhir (JSON, skema v2)", status_label: "Status pelabelan (final)",
  catatan: "Riwayat proses: sumber transkrip, perapian ejaan, sumber label",
};
const ex = S.contoh;
const children = [
  new Paragraph({ children: [new TextRun("SISIP_L7_MULAI")] }),
  new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 120, after: 80 }, children: [run("Lampiran 7. Data Card dan Struktur Dataset", { bold: true, size: 24 })] }),
  P("Lampiran ini mendokumentasikan dataset perintah suara yang menjadi luaran tambahan: ringkasan (data card), struktur berkas dan kolom metadata, skema label, proses pelabelan, serta contoh satu baris data. Seluruh angka dihitung dari dataset/metadata.csv (luaran/statistik_dataset.py).", { first: true }),
  CAP("Tabel L.2. Ringkasan Dataset (Data Card)"),
  T(["Item", "Isi"], [
    ["Nama", "Dataset Perintah Suara Robot Layanan Laboratorium Berbahasa Indonesia (kalimat bebas; formal, semi-formal, informal)"],
    ["Pembuat", "As'ad Bahauddin Ahmad; Vivi Tri Widyaningrum — Teknik Mekatronika, Universitas Trunojoyo Madura"],
    ["Program", "Asistensi Hibah Penelitian (MBKM Riset), LPPM UTM 2026"],
    ["Responden", `${S.responden.length} orang: ${resp}`],
    ["Jumlah ujaran", `${S.n} (${Object.values(S.penutur)[0]} per responden; 27 per intent; 54 per tingkat formalitas)`],
    ["Durasi", `Total ${n2(D.total_menit, 1)} menit; ${n2(D.mean)} ± ${n2(D.sd)} detik per ujaran (${n2(D.min)}–${n2(D.max)} detik)`],
    ["Panjang transkrip", `${n2(K.mean)} ± ${n2(K.sd)} kata per ujaran (${K.min}–${K.max} kata); total ${K.total.toLocaleString("id-ID")} kata`],
    ["Format audio", "WAV, 16 kHz, mono, PCM 16-bit (direkam 48 kHz lalu di-resample dengan soxr HQ)"],
    ["Perangkat dan lokasi", "Mikrofon wireless lavalier dengan receiver USB (limiter dan noise gate bawaan); Laboratorium Sistem Otomasi, Teknik Mekatronika UTM"],
    ["Cara elisitasi", "Kalimat bebas berdasarkan 54 kartu skenario (intent, entitas target, gaya bahasa); responden tidak membaca kalimat"],
    ["Label per ujaran", "Transkrip manual, intent (6 kelas), entitas (room/object/person/document), steps (perintah majemuk), formalitas, kode responden"],
    ["Entitas terisi", `person ${E.person}, room ${E.room}, object ${E.object}, document ${E.document}; ${S.intent.combined_command} perintah majemuk masing-masing ${Object.keys(S.steps_combined).join("/")} langkah`],
    ["Penggunaan", "Hanya sebagai set uji; tidak dipakai melatih atau menyetel metode apa pun"],
    ["Privasi", "Nama tidak disimpan bersama rekaman; audio tidak diunggah ke repositori publik; lembar persetujuan pada Lampiran 4"],
    ["Lisensi", "[ISI: lisensi distribusi dataset, mis. CC BY-NC 4.0, sesuai keputusan tim/LPPM]"],
  ], [3, 12]),
  CAP("Tabel L.3. Struktur Berkas Dataset"),
  T(["Berkas / folder", "Isi"], [
    ["dataset/R01/, R02/, R03/", "Audio per responden, 54 berkas WAV masing-masing (mis. R01/R01_S31.wav)"],
    ["dataset/metadata.csv", "Satu baris per ujaran (162 baris, 24 kolom; Tabel L.4)"],
    ["dataset/responden.csv", "Usia, jenis kelamin, bahasa ibu, status persetujuan, tanggal (tanpa nama)"],
    ["dataset/SHA256SUMS.txt", "Checksum SHA-256 setiap berkas untuk verifikasi keutuhan"],
    ["bench/skenario_dataset.json", "54 kartu skenario (intent, entitas target, gaya bahasa)"],
    ["config/domain_id.yaml", "Daftar nilai entitas kanonik dan aliasnya"],
  ], [5, 10], [0]),
  CAP("Tabel L.4. Kolom metadata.csv"),
  T(["Kolom", "Keterangan"], S.kolom.map((k) => [k, KOLOM[k] || ""]), [4, 11], [0]),
  CAP("Tabel L.5. Skema Label (JSON, skema v2)"),
  T(["Field", "Tipe", "Keterangan"], [
    ["intent", "string", "Salah satu dari navigate_room, navigate_object, find_person, deliver_document, combined_command, general_command"],
    ["room", "string | null", "Ruangan tujuan (nama kanonik, mis. ruang pak umam)"],
    ["object", "string | null", "Benda/alat tujuan (mis. mesin cnc, trainer plc)"],
    ["person", "string | null", "Orang yang dicari atau penerima dokumen (mis. bu vivi)"],
    ["document", "string | null", "Dokumen yang diantar (mis. jadwal praktikum)"],
    ["steps", "array | null", "Hanya untuk combined_command: daftar langkah (intent + 4 entitas); field tingkat atas bernilai null"],
  ], [2.4, 2.6, 10], [0]),
  H3("Proses Pelabelan"),
  P(`1. Perekaman dengan kartu skenario dan pemeriksaan level otomatis (rekam ulang bila terlalu pelan atau clipping berat).`),
  P(`2. Draf transkrip dari dua konfigurasi Whisper berbeda ditampilkan berdampingan untuk mengurangi anchoring; peneliti mendengarkan audio dan menetapkan transkrip ground-truth (diketik sendiri ${S.sumber_transkrip["sumber=ketik"] ?? 0}, draf 1 ${S.sumber_transkrip["sumber=draf1"] ?? 0}, draf 2 ${S.sumber_transkrip["sumber=draf2"] ?? 0}).`),
  P("3. Konvensi transkrip: semua kata yang diucapkan ditulis (termasuk partikel), bunyi ragu tidak ditulis, nama sesuai kamus, dan kata depan dipisah sesuai EYD (pemeriksaan otomatis)."),
  P(`4. Label disusun dari apa yang benar-benar diucapkan, dengan draf dari target kartu (bukan dari keluaran metode yang diuji). Entitas yang tidak diucapkan bernilai null; nilai dinormalisasi ke nama kanonik dan divalidasi terhadap skema v2. Hasil: ${S.label_sama_target} dari ${S.n} label sama dengan target kartu dan ${S.n - S.label_sama_target} diubah.`),
  P("5. Pemeriksaan kebocoran data terhadap set pengembangan, data latih IndoBERT, dan contoh prompt: 0 kalimat sama; 2 kalimat mirip (Jaccard 0,83) diuji dengan analisis sensitivitas."),
  P("Keterbatasan: pelabelan dilakukan oleh satu anotator (peneliti) tanpa pengukuran kesepakatan antar-anotator.", { after: 160 }),
  CAP("Tabel L.6. Contoh Satu Baris Data"),
  T(["Kolom", "Nilai"], [["penutur / item_id", `${ex.penutur} / ${ex.item_id}`], ["formality", ex.formality], ["tujuan (kartu)", ex.tujuan], ["wav", ex.wav],
    ["durasi_s", ex.durasi_s.replace(".", ",")], ["transkrip", ex.transkrip], ["label_final_json", ex.label_final_json], ["status_label", ex.status_label]], [4, 11], [0]),
  new Paragraph({ children: [new TextRun("SISIP_L7_SELESAI")] }),
];
const doc = new Document({ sections: [{ children }] });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[3], b); console.log("ditulis", process.argv[3]); });
