"""Draf artikel JoTI: mengisi 'Template JoTI Baru 2025.docx' (gaya, header, kotak info, logo dipertahankan).
Semua angka dari results/eval_dataset_MSI_20261112_095743.md dan results/analisis_dataset_MSI_20261112_104423.md.

    python luaran/buat_artikel_joti.py "Template JoTI Baru 2025.docx" Artikel_JoTI_DRAF.docx
Markup teks: _miring_ (di batas kata), **tebal**, [ISI ...] disorot kuning, [n] sitasi IEEE.
"""
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
GBR = ROOT / "luaran" / "gambar"
SEG = '<w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI" w:cs="Segoe UI"/>'

# ---------------------------------------------------------------- isi naskah
JUDUL = "Evaluasi Large Language Model Qwen2.5 untuk Ekstraksi Intent Perintah Suara Robot Berbahasa Indonesia secara Offline"
ABSTRAK = (
    "Voice-controlled robots need to understand free-form commands, yet small large language models (LLMs) have rarely "
    "been evaluated for Indonesian. This study evaluates Qwen2.5 1.5B (Q4_K_M, Ollama) as the natural language "
    "understanding component of a fully offline pipeline consisting of Silero VAD, Whisper base, and structured JSON "
    "output, and compares it with rule-based keyword matching and a fine-tuned IndoBERT classifier. A test set of 162 "
    "free-form utterances was recorded from three speakers using scenario cards covering six intents and three formality "
    "levels. With ground-truth text, Qwen2.5 achieved 75.31% intent accuracy and 65.43% exact match, below IndoBERT "
    "(96.30%, 85.19%) and rule-based matching (85.80%, 85.19%). In the full speech pipeline, Whisper base reached a word "
    "error rate of 30.78%, and exact match dropped to 45.68% for Qwen2.5, 61.11% for rule-based matching, and 56.17% for "
    "IndoBERT. Most Qwen2.5 errors came from multi-step commands, of which only 1 of 27 was recognized. On a laptop GPU "
    "the mean response time was 2.42 s. The results indicate that, in a narrow robot domain, a small prompted LLM does "
    "not yet outperform a lightweight supervised classifier, and that speech recognition errors dominate end-to-end failures."
)
KATA_KUNCI = "Indonesian, Intent extraction, Large language model, Qwen2.5, Speech recognition, Whisper"

# Tiap entri: ("H", judul bagian) | ("S", sub judul) | ("SS", sub-sub judul) | ("P", paragraf) |
# ("FIG", berkas, lebar_cm, keterangan) | ("TAB", judul, header, baris, lebar_kolom_cm) | ("EQ", teks, nomor)
ISI = [
    ("H", "PENDAHULUAN"),
    ("P", "Robot layanan di lingkungan kerja seperti laboratorium idealnya dapat diperintah dengan bahasa sehari-hari. "
          "Antarmuka suara konvensional umumnya hanya mengenali perintah berstruktur tetap, sehingga gagal ketika pengguna "
          "menyusun kalimat dengan diksi, urutan kata, atau tingkat formalitas yang berbeda. Pemahaman perintah semacam ini "
          "merupakan tugas _natural language understanding_ (NLU), yaitu mengenali maksud (_intent_) dan entitas dari "
          "sebuah ujaran [1], [2]."),
    ("P", "Sejak hadirnya _large language model_ (LLM), sejumlah penelitian interaksi manusia–robot memakai LLM praterlatih "
          "sebagai komponen NLU. Nwankwo dan Rueckert menunjukkan bahwa robot otonom dapat memahami instruksi kalimat bebas "
          "melalui LLM tanpa data latih _intent_ khusus [3], dan Ahn dkk. memadukan LLM dengan kemampuan robot untuk "
          "menerjemahkan instruksi bahasa alami menjadi tindakan [4]. Namun, penelitian tersebut memakai Bahasa Inggris dan "
          "model berukuran besar yang berjalan di server. Untuk Bahasa Indonesia, model berbasis _transformer_ seperti "
          "IndoBERT [5], [6] telah banyak dipakai untuk klasifikasi teks, sedangkan evaluasi pengenalan suara Whisper [7] "
          "untuk Bahasa Indonesia menunjukkan kinerja yang masih dipengaruhi variasi cara bicara [8], [9]."),
    ("P", "Celah yang diisi penelitian ini adalah belum adanya perbandingan sistematis antara LLM kecil yang berjalan "
          "sepenuhnya _offline_ dan metode konvensional untuk ekstraksi _intent_ perintah robot berbahasa Indonesia yang "
          "diucapkan secara bebas. Penelitian ini mengevaluasi Qwen2.5 1.5B [10] dalam _pipeline_ suara-ke-JSON dan "
          "membandingkannya dengan _rule-based keyword matching_ dan IndoBERT _fine-tuned_. Pertanyaan penelitiannya adalah: "
          "(1) seberapa akurat Qwen2.5 mengekstrak _intent_ dan entitas dari perintah kalimat bebas, (2) berapa _latency_ "
          "_pipeline_ dari suara hingga JSON, dan (3) bagaimana perbandingannya dengan kedua metode pembanding pada tiga "
          "tingkat formalitas. [ISI: tambahkan 2–3 rujukan artikel JoTI yang relevan, sesuai ketentuan 20% rujukan JoTI.]"),

    ("H", "METODE"),
    ("S", "Rancangan Sistem"),
    ("P", "_Pipeline_ terdiri atas empat tahap. Audio mikrofon _wireless lavalier_ direkam pada 48 kHz, digabung menjadi mono, "
          "dan di-_resample_ ke 16 kHz. Silero VAD [11] mendeteksi ujaran per _frame_ 32 ms dengan _pre-roll_ 300 ms dan "
          "jeda diam 1,2 detik sebagai penanda akhir perintah. Whisper base dijalankan melalui faster-whisper [12] dengan "
          "bahasa Indonesia, _beam_ 5, _temperature_ 0, dan _initial prompt_ berisi nama entitas domain. Transkrip kemudian "
          "diproses oleh metode NLU yang menghasilkan JSON dengan field intent, room, object, person, document, dan steps. "
          "Field steps berisi daftar sub-perintah dan hanya dipakai untuk perintah majemuk. JSON ini merupakan antarmuka ke pengendali robot; penggerakan robot fisik berada di luar ruang lingkup penelitian ini. Seluruh komponen berjalan "
          "_offline_ pada laptop (Intel Core i5-12450H, RAM 7,7 GB, NVIDIA RTX 2050 4 GB) dalam dua skenario: dengan GPU "
          "dan hanya CPU."),
    ("P", "Enam kategori _intent_ yang digunakan adalah navigate_room, navigate_object, find_person, deliver_document, "
          "combined_command (dua tindakan berurutan dalam satu kalimat), dan general_command (misalnya berhenti atau kembali "
          "ke posisi awal)."),
    ("S", "Metode NLU yang Dibandingkan"),
    ("P", "**Qwen2.5 1.5B** (kuantisasi Q4_K_M) dijalankan melalui Ollama dengan _system prompt_ berbahasa Indonesia berisi "
          "enam contoh _few-shot_ dan _structured output_ berbasis JSON Schema yang dikunci per _intent_, _temperature_ 0, dan "
          "_seed_ 42. Iterasi _prompt_ hanya dilakukan pada set pengembangan dan dihentikan setelah dua versi untuk mencegah "
          "_overfitting_. **Rule-based keyword matching** memetakan kata kunci per _intent_ dan memecah perintah majemuk "
          "berdasarkan kata penghubung. **IndoBERT** (indobenchmark/indobert-base-p1) [5] di-_fine-tune_ untuk klasifikasi "
          "_intent_ dengan 300 kalimat latih sintetis (50 per _intent_); perintah majemuk dipecah per klausa sebelum "
          "diklasifikasi. Ketiga metode memakai kamus entitas dan normalisasi yang sama sehingga perbandingan adil."),
    ("S", "Dataset"),
    ("P", "Set uji direkam dari tiga responden (satu berbahasa ibu Madura, dua Jawa). Setiap responden menerima 54 kartu "
          "skenario berisi _intent_, entitas target, dan gaya bahasa (formal, semi-formal, informal), lalu mengucapkan "
          "perintah dengan kalimatnya sendiri, bukan membaca kalimat. Hasilnya 162 ujaran (27 per _intent_, 54 per tingkat "
          "formalitas) berformat WAV 16 kHz mono. Transkrip _ground-truth_ dikoreksi manual, dan label disusun dari apa yang "
          "benar-benar diucapkan. Pemeriksaan kebocoran data memastikan tidak ada kalimat uji yang sama dengan set "
          "pengembangan, data latih IndoBERT, maupun contoh _prompt_. Parameter VAD dan pilihan implementasi Whisper "
          "ditetapkan dari set pengembangan terpisah (36 kalimat dibaca dan 18 perintah bebas dari satu penutur) [ISI: sebutkan bila penutur ini juga salah satu responden], bukan "
          "dari set uji."),
    ("S", "Prosedur Pengujian dan Metrik"),
    ("P", "Ketiga metode diuji pada tiga masukan: teks _ground-truth_ (galat NLU saja), rekaman utuh yang ditranskripsi "
          "Whisper, dan _pipeline_ lengkap (VAD lalu Whisper). Akurasi transkripsi diukur dengan _word error rate_ (WER):"),
    ("EQ", "WER = (S + D + I) / N", "1"),
    ("P", "dengan S, D, dan I berturut-turut jumlah kata tersubstitusi, terhapus, dan tersisip, serta N jumlah kata "
          "referensi. NLU diukur dengan _intent accuracy_, _exact match_ (EM: _intent_ serta seluruh entitas dan langkah "
          "harus tepat), F1, dan _confusion matrix_. _Latency_ dicatat per tahap; waktu respons adalah jeda tunggu VAD "
          "ditambah waktu Whisper dan NLU. Perbedaan antarmetode pada item yang sama diuji dengan uji McNemar eksak [13]."),

    ("H", "HASIL DAN PEMBAHASAN"),
    ("S", "Latency dan Akurasi Transkripsi"),
    ("TAB", "Tabel 1. Latency Pipeline per Tahap (rata-rata ± SD, n = 162)",
     ["Platform", "VAD (s)", "Whisper (s)", "Qwen2.5 (s)", "Total (s)", "Respons (s)"],
     [["Laptop GPU", "0,076 ± 0,088", "0,200 ± 0,114", "1,024 ± 0,433", "1,300 ± 0,604", "2,424 ± 0,528"],
      ["Laptop CPU", "0,069 ± 0,056", "1,346 ± 1,231", "2,822 ± 1,825", "4,237 ± 2,826", "5,368 ± 2,791"]],
     [2.6, 2.4, 2.4, 2.4, 2.4, 2.4]),
    ("P", "Tabel 1 menunjukkan bahwa Qwen2.5 menyumbang sebagian besar waktu komputasi. Pada laptop GPU seluruh ujaran "
          "selesai di bawah 4,4 detik. Pada laptop CPU rata-rata waktu respons 5,37 detik, tetapi 4 dari 162 ujaran melebihi "
          "15 detik (maksimum 26,0 detik); keempatnya terjadi ketika RAM tersedia kurang dari 0,5 GB, sehingga diduga "
          "disebabkan _swap_ memori. Metode pembanding jauh lebih ringan: waktu NLU _rule-based_ 0,001 detik dan IndoBERT "
          "0,037 detik di GPU. WER Whisper base pada 162 ujaran adalah 31,44% untuk rekaman utuh dan 30,78% untuk segmen VAD. "
          "Kesalahan terbanyak terjadi pada nama orang dan kata umum, misalnya \"carikan\" yang ditranskripsi sebagai "
          "\"jarikan\". Pada set pengembangan, _initial prompt_ domain menurunkan WER dari 56,25% menjadi 38,75%."),
    ("S", "Akurasi Ekstraksi Intent dan Entitas"),
    ("FIG", "akurasi_id.png", 15.5, "Gambar 1. Intent Accuracy dan Exact Match pada Tiga Jenis Masukan (Laptop GPU, n = 162)"),
    ("P", "Gambar 1 memperlihatkan bahwa pada teks _ground-truth_ IndoBERT memperoleh _intent accuracy_ tertinggi (96,30%), "
          "diikuti _rule-based_ (85,80%) dan Qwen2.5 (75,31%). EM _rule-based_ dan IndoBERT sama (85,19%), sedangkan Qwen2.5 "
          "65,43%. Ketika masukan berupa transkrip, EM turun 19,8 poin (Qwen2.5), 24,1 poin (_rule-based_), dan 29,0 poin "
          "(IndoBERT), sehingga pada _pipeline_ lengkap _rule-based_ memperoleh EM tertinggi (61,11%) dan IndoBERT tetap "
          "unggul dalam _intent accuracy_ (83,95%). Uji McNemar menunjukkan keunggulan IndoBERT atas Qwen2.5 dalam _intent_ "
          "bermakna pada semua masukan (p < 0,001), sedangkan _intent accuracy_ Qwen2.5 dan _rule-based_ pada _pipeline_ "
          "lengkap tidak berbeda bermakna (p = 0,71). Hasil Qwen2.5 pada CPU sedikit berbeda dari GPU (teks: 78,40% dan "
          "70,99%) karena perbedaan numerik, sehingga hasil dilaporkan per platform."),
    ("FIG", "formalitas_id.png", 15.5, "Gambar 2. Intent Accuracy per Tingkat Formalitas (Laptop GPU, n = 54 per kelompok)"),
    ("P", "Pada kalimat formal dan semi-formal, _intent accuracy_ Qwen2.5 adalah 78,70% pada teks dan 62,04% pada _pipeline_ "
          "lengkap, di bawah target 80% yang ditetapkan. Pada kalimat informal (Gambar 2), Qwen2.5 (64,8%) setara dengan "
          "_rule-based_ (63,0%) tetapi di bawah IndoBERT (79,6%) pada _pipeline_ lengkap, sehingga dugaan bahwa LLM lebih "
          "tahan terhadap kalimat informal tidak terdukung oleh data ini."),
    ("S", "Analisis Kesalahan"),
    ("FIG", "cm_qwen_id.png", 8.5, "Gambar 3. Confusion Matrix Qwen2.5 pada Masukan Teks"),
    ("P", "Gambar 3 menunjukkan bahwa kesalahan Qwen2.5 terpusat pada dua pola. Dari 27 perintah majemuk, hanya satu yang "
          "dikenali; sisanya diprediksi sebagai perintah tunggal, terutama navigasi (12 ke navigate_room dan 8 ke "
          "navigate_object). Selain itu, 13 dari 27 perintah umum seperti \"kembali ke posisi semula\" dianggap navigasi ke "
          "ruangan. Untuk navigate_object, find_person, dan deliver_document, F1 Qwen2.5 mencapai 0,86–0,96. IndoBERT "
          "unggul pada perintah majemuk (F1 0,88 berbanding 0,07) karena kalimat dipecah per klausa sebelum klasifikasi, "
          "sedangkan Qwen2.5 harus menentukan struktur majemuk sendiri dalam satu langkah generasi."),
    ("P", "Temuan ini melengkapi laporan bahwa LLM dapat memahami instruksi bebas untuk robot [3], [4]: pada model 1,5 miliar "
          "parameter dengan Bahasa Indonesia, pemahaman perintah tunggal sudah baik, tetapi keputusan struktural seperti "
          "memecah perintah majemuk belum andal. Di sisi lain, akurasi _baseline_ yang mencapai 100% pada set pengembangan "
          "turun pada kalimat bebas responden, yang menegaskan pentingnya menguji dengan kalimat yang tidak disusun dari "
          "kosakata kamus atau data latih. Keterbatasan penelitian ini adalah jumlah responden yang kecil (tiga orang, satu "
          "di antaranya berbahasa ibu Madura) dan pengujian yang dilakukan pada laptop, bukan perangkat _embedded_."),

    ("H", "KESIMPULAN DAN SARAN"),
    ("P", "Pada 162 perintah kalimat bebas berbahasa Indonesia, Qwen2.5 1.5B yang berjalan _offline_ mencapai _intent "
          "accuracy_ 75,31% dan EM 65,43% pada teks, serta 62,96% dan 45,68% pada _pipeline_ suara lengkap, lebih rendah "
          "daripada IndoBERT _fine-tuned_ (96,30%; 83,95%) yang dilatih hanya dengan 300 kalimat sintetis. Kelemahan utama "
          "Qwen2.5 adalah perintah majemuk, sedangkan sumber galat terbesar _pipeline_ adalah transkripsi Whisper base (WER "
          "±31%). Dari sisi waktu, _pipeline_ memberikan respons rata-rata 2,42 detik pada laptop GPU dan 5,37 detik pada CPU. "
          "Penelitian lanjutan disarankan untuk memecah klausa sebelum diproses LLM atau menambah contoh perintah majemuk, "
          "menguji model yang lebih besar, meningkatkan ASR dengan Whisper small atau _fine-tuning_, menguji pada Raspberry "
          "Pi 5, dan menambah jumlah serta keragaman responden."),

    ("H", "UCAPAN TERIMA KASIH"),
    ("P", "Penelitian ini didukung Program Asistensi Hibah Penelitian (MBKM Riset) LPPM Universitas Trunojoyo Madura. "
          "Penulis berterima kasih kepada Laboratorium Sistem Otomasi, Program Studi Teknik Mekatronika, dan para responden "
          "yang bersedia direkam. [ISI: sesuaikan]"),
]

PUSTAKA = [
    "C. Coucke et al., \"Snips Voice Platform: An embedded spoken language understanding system for private-by-design voice interfaces,\" _arXiv preprint_ arXiv:1805.10190, 2018.",
    "S. Larson et al., \"An evaluation dataset for intent classification and out-of-scope prediction,\" in _Proc. EMNLP-IJCNLP_, Hong Kong, 2019, pp. 1311–1316.",
    "L. Nwankwo and E. Rueckert, \"The conversation is the command: Interacting with real-world autonomous robots through natural language,\" in _Companion of the 2024 ACM/IEEE Int. Conf. Human-Robot Interaction_, 2024, pp. 284–288, doi: 10.1145/3610978.3640723.",
    "M. Ahn et al., \"Do as I can, not as I say: Grounding language in robotic affordances,\" _arXiv preprint_ arXiv:2204.01691, 2022.",
    "B. Wilie et al., \"IndoNLU: Benchmark and resources for evaluating Indonesian natural language understanding,\" in _Proc. 1st Conf. Asia-Pacific Chapter of the ACL_, 2020, pp. 843–857.",
    "F. Koto, A. Rahimi, J. H. Lau, and T. Baldwin, \"IndoLEM and IndoBERT: A benchmark dataset and pre-trained language model for Indonesian NLP,\" in _Proc. 28th Int. Conf. Computational Linguistics (COLING)_, 2020, pp. 757–770.",
    "A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, \"Robust speech recognition via large-scale weak supervision,\" in _Proc. 40th Int. Conf. Machine Learning (PMLR 202)_, 2023, pp. 28492–28518.",
    "A. Adila, D. Lestari, A. Purwarianti, D. Tanaya, K. Azizah, and S. Sakti, \"Enhancing Indonesian automatic speech recognition: Evaluating multilingual models with diverse speech variabilities,\" _arXiv preprint_ arXiv:2410.08828, 2024.",
    "I. A. N. Fathony, A. Mareta, B. E. Adiana, O. Wardhani, and D. A. Halim, \"Optimisasi Whisper speech-to-text Bahasa Indonesia dengan hybrid cloud dan multi-engine,\" _ELKOM: Jurnal Elektronika dan Komputer_, vol. 18, no. 1, pp. 60–72, 2025, doi: 10.51903/5n2d3s08.",
    "Qwen Team, \"Qwen2.5 technical report,\" _arXiv preprint_ arXiv:2412.15115, 2024.",
    "Silero Team, \"Silero VAD: Pre-trained enterprise-grade voice activity detector,\" GitHub, 2024. [Online]. Available: https://github.com/snakers4/silero-vad",
    "SYSTRAN, \"faster-whisper: Faster Whisper transcription with CTranslate2,\" GitHub, 2024. [Online]. Available: https://github.com/SYSTRAN/faster-whisper",
    "Q. McNemar, \"Note on the sampling error of the difference between correlated proportions or percentages,\" _Psychometrika_, vol. 12, no. 2, pp. 153–157, 1947.",
    "[ISI: rujukan artikel JoTI 1]",
    "[ISI: rujukan artikel JoTI 2]",
]


# ---------------------------------------------------------------- XML helper
def rpr(sz=22, b=False, i=False, hl=False, extra=""):
    return ("<w:rPr>" + SEG + ("<w:b/><w:bCs/>" if b else "") + ("<w:i/><w:iCs/>" if i else "") + extra +
            ('<w:highlight w:val="yellow"/>' if hl else "") + f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
            '<w:lang w:val="id-ID"/></w:rPr>')


def runs(text, sz=22, b=False, i=False):
    out, last = [], 0
    pat = re.compile(r"(\*\*[^*]+\*\*|(?<![\w])_[^_]+?_(?![\w])|\[ISI[^\]]*\])")
    for m in pat.finditer(text):
        if m.start() > last:
            out.append((text[last:m.start()], b, i, False))
        t = m.group(0)
        if t.startswith("**"):
            out.append((t[2:-2], True, i, False))
        elif t.startswith("_"):
            out.append((t[1:-1], b, True, False))
        else:
            out.append((t, True, i, True))
        last = m.end()
    if last < len(text):
        out.append((text[last:], b, i, False))
    return "".join(f'<w:r>{rpr(sz, bb, ii, hh)}<w:t xml:space="preserve">{escape(s)}</w:t></w:r>' for s, bb, ii, hh in out)


def para(ppr, text, **k):
    return f"<w:p>{ppr}{runs(text, **k)}</w:p>"


BODY_PPR = ('<w:pPr><w:pStyle w:val="BodyText"/><w:ind w:right="-2" w:firstLine="720"/><w:jc w:val="both"/>'
            f'<w:rPr>{SEG}<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:pPr>')
NOIND_PPR = ('<w:pPr><w:pStyle w:val="BodyText"/><w:ind w:right="-2"/><w:jc w:val="both"/>'
             f'<w:rPr>{SEG}<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:pPr>')
CENTER_PPR = ('<w:pPr><w:pStyle w:val="BodyText"/><w:keepNext/><w:ind w:right="-2"/><w:jc w:val="center"/>'
              f'<w:rPr>{SEG}<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:pPr>')
CAP_PPR = ('<w:pPr><w:pStyle w:val="BodyText"/><w:spacing w:after="120"/><w:ind w:right="-2"/><w:jc w:val="center"/>'
           f'<w:rPr>{SEG}<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:pPr>')
H_PPR = ('<w:pPr><w:keepNext/><w:spacing w:before="240"/><w:jc w:val="both"/>'
         f'<w:rPr>{SEG}<w:b/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:pPr>')
S_PPR = ('<w:pPr><w:pStyle w:val="BodyText"/><w:keepNext/><w:spacing w:before="120"/><w:ind w:right="-2"/>'
         f'<w:rPr>{SEG}<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:pPr>')
EMPTY = f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:rPr>{SEG}<w:sz w:val="22"/></w:rPr></w:pPr></w:p>'


def table(header, rows, widths_cm):
    w = [int(c * 567) for c in widths_cm]
    def cell(txt, k, top, bottom, bold):
        b = ""
        if top:
            b += '<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        if bottom:
            b += '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w[k]}" w:type="dxa"/><w:tcBorders>{b}</w:tcBorders>'
                '<w:tcMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tcMar></w:tcPr>'
                f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:jc w:val="{"left" if k == 0 else "center"}"/></w:pPr>'
                f'{runs(txt, sz=18, b=bold)}</w:p></w:tc>')
    out = ('<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:jc w:val="center"/><w:tblLayout w:type="fixed"/></w:tblPr>'
           "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{x}"/>' for x in w) + "</w:tblGrid>")
    out += '<w:tr><w:trPr><w:tblHeader/><w:jc w:val="center"/></w:trPr>' + "".join(cell(h, k, True, True, True) for k, h in enumerate(header)) + "</w:tr>"
    for r_i, r in enumerate(rows):
        out += '<w:tr><w:trPr><w:jc w:val="center"/></w:trPr>' + "".join(cell(c, k, False, r_i == len(rows) - 1, False) for k, c in enumerate(r)) + "</w:tr>"
    return out + "</w:tbl>"


def figure(rid, pid, file, width_cm):
    from struct import unpack
    with open(GBR / file, "rb") as f:
        head = f.read(24)
    wpx, hpx = unpack(">II", head[16:24])
    cx = int(width_cm * 360000)
    cy = int(cx * hpx / wpx)
    return (f'<w:p>{CENTER_PPR}<w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{pid}" name="Gambar {pid}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="{pid}" name="{file}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>")


def set_text(block, old_substr_re, new_runs_xml):
    """Ganti seluruh run dalam paragraf pertama di `block` yang teksnya cocok dengan regex."""
    for p in re.findall(r"<w:p[ >].*?</w:p>", block, re.S):
        t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
        if re.search(old_substr_re, t):
            ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
            start = p[: p.index(">") + 1]
            return block.replace(p, start + (ppr.group(0) if ppr else "") + new_runs_xml + "</w:p>", 1)
    raise ValueError(f"tidak ditemukan: {old_substr_re}")


# ---------------------------------------------------------------- rakit
def main():
    tpl, out = Path(sys.argv[1]), Path(sys.argv[2])
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(tpl) as z:
        z.extractall(tmp)
    for p in tmp.rglob("*"):
        if p.is_symlink():
            p.unlink()
    doc_p = tmp / "word" / "document.xml"
    x = doc_p.read_text(encoding="utf-8")
    b0 = x.index("<w:body>") + len("<w:body>")
    body = x[b0:x.index("</w:body>")]
    blocks = re.findall(r"(<w:p[ >].*?</w:p>|<w:tbl>.*?</w:tbl>|<w:sectPr.*?</w:sectPr>)", body, re.S)
    assert "PENDAHULUAN" in "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", blocks[9])), "struktur template berubah"
    head = blocks[:9]
    tail = blocks[77:]  # paragraf kosong + sectPr

    # judul
    head[0] = set_text(head[0], "Judul", runs(JUDUL, sz=32, b=True).replace("<w:rPr>", '<w:rPr><w:color w:val="002060"/>'))
    # penulis & afiliasi
    SUP = '<w:vertAlign w:val="superscript"/>'
    sup = lambda s: f'<w:r>{rpr(22, True, extra=SUP)}<w:t>{s}</w:t></w:r>'
    head[1] = set_text(head[1], "Nama Penulis", runs("[ISI: Nama Penulis 1 tanpa gelar]", b=True) + sup("1*") +
                       runs(", [ISI: Nama Penulis 2 tanpa gelar]", b=True) + sup("2"))
    head[2] = set_text(head[2], "Program Studi", f'<w:r>{rpr(20, extra=SUP)}<w:t>1,2</w:t></w:r>' +
                       runs("Program Studi Teknik Mekatronika, Universitas Trunojoyo Madura, Bangkalan, Jawa Timur, Indonesia", sz=20))
    head[3] = ""  # afiliasi ke-3 (contoh luar negeri) dihapus
    head[4] = set_text(head[4], "e-mail", runs("e-mail: [ISI: email penulis 1]", sz=20) + sup("1*") + runs(", [ISI: email penulis 2]", sz=20) + sup("2"))
    head[5] = set_text(head[5], "Kontak WA", runs("Kontak WA: [ISI] (hanya untuk komunikasi, dihapus saat publish)", sz=20))
    # kotak informasi artikel (tabel)
    info = head[7]
    info = set_text(info, "A maximum 200 word", runs(ABSTRAK, sz=20, i=True))
    info = set_text(info, "Ditulis Bahasa Inggris", runs(KATA_KUNCI, sz=20, i=True))
    info = set_text(info, "^…+", runs("[ISI: email penulis korespondensi]", sz=20))
    head[7] = info

    # isi
    rels_p = tmp / "word" / "_rels" / "document.xml.rels"
    rels = rels_p.read_text(encoding="utf-8")
    media = tmp / "word" / "media"
    gen, pid, n_fig = [], 900, 0
    for item in ISI:
        kind = item[0]
        if kind == "H":
            if gen:
                gen.append(EMPTY)
            gen.append(f'<w:p>{H_PPR}{runs(item[1], b=True)}</w:p>')
        elif kind == "S":
            gen.append(f'<w:p>{S_PPR}{runs(item[1], b=True)}</w:p>')
        elif kind == "SS":
            gen.append(f'<w:p>{S_PPR}{runs(item[1], b=True, i=True)}</w:p>')
        elif kind == "P":
            gen.append(para(BODY_PPR, item[1]))
        elif kind == "EQ":
            gen.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:tabs><w:tab w:val="center" w:pos="4535"/><w:tab w:val="right" w:pos="9070"/></w:tabs></w:pPr>'
                       f'<w:r>{rpr()}<w:tab/></w:r>{runs(item[1], i=True)}<w:r>{rpr()}<w:tab/><w:t>({item[2]})</w:t></w:r></w:p>')
        elif kind == "FIG":
            n_fig += 1
            rid = f"rIdFig{n_fig}"
            shutil.copy(GBR / item[1], media / f"fig{n_fig}.png")
            rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/fig{n_fig}.png"/></Relationships>')
            pid += 1
            gen.append(figure(rid, pid, item[1], item[2]))
            gen.append(para(CAP_PPR, item[3]))
        elif kind == "TAB":
            gen.append(para(CENTER_PPR, item[1]))
            gen.append(table(item[2], item[3], item[4]))
            gen.append(EMPTY)
    gen.append(EMPTY)
    gen.append(f'<w:p>{H_PPR}{runs("DAFTAR PUSTAKA", b=True)}</w:p>')
    ref_ppr = re.search(r"<w:pPr>.*?</w:pPr>", blocks[64], re.S).group(0)
    for r in PUSTAKA:
        gen.append(para(ref_ppr, r))
    rels_p.write_text(rels, encoding="utf-8")
    new_body = "".join(head) + "".join(gen) + "".join(tail)
    doc_p.write_text(x[:b0] + new_body + x[x.index("</w:body>"):], encoding="utf-8")
    ct = tmp / "[Content_Types].xml"
    c = ct.read_text(encoding="utf-8")
    if 'Extension="png"' not in c:
        ct.write_text(c.replace("<Types ", "<Types ").replace("</Types>", '<Default Extension="png" ContentType="image/png"/></Types>'), encoding="utf-8")
    # zip tanpa entri folder; [Content_Types].xml pertama
    files = sorted((p for p in tmp.rglob("*") if p.is_file()), key=lambda p: (p.name != "[Content_Types].xml", str(p)))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(tmp).as_posix())
    shutil.rmtree(tmp)
    words = len(" ".join(t for k, *r in ISI if k == "P" for t in [r[0]]).split())
    print(f"ditulis {out} | gambar {n_fig} | kata isi ±{words} | kata abstrak {len(ABSTRAK.split())} | kata judul {len(JUDUL.split())}")


if __name__ == "__main__":
    main()
