"""F8 - Koreksi transkrip manual (ground-truth) untuk dataset responden.

Untuk tiap rekaman: audio diputar otomatis, lalu ditampilkan dua draf dari dua konfigurasi Whisper yang
berbeda (agar penilai tidak hanya terpaku pada satu sistem). Penilai menulis transkrip yang BENAR
sesuai yang terdengar.

Perintah:
  r            putar ulang
  1 / 2        draf 1 / draf 2 sudah persis benar -> dipakai apa adanya
  <teks>       ketik transkrip yang benar
  s            lewati          q   keluar (progres tersimpan; jalankan lagi untuk melanjutkan)

Konvensi transkrip (lihat Dokumentasi/F3_whisper.md):
  - tulis SEMUA kata yang diucapkan, termasuk partikel (ya, dong, gih, deh) dan kata gaul/daerah apa adanya
  - jangan tulis bunyi ragu murni (eh, em, hmm); nama orang/tempat ditulis sesuai kamus (Pak Umam, lab otomasi)
  - angka ditulis dengan huruf; tanda baca boleh (diabaikan saat WER)
  - kata depan ditulis TERPISAH (EYD): "ke ruang dosen", "ke lengan robot", "di ruang asisten"
    (bukan "keruang", "kelengan"). Alat ini memperingatkan bila menemukan bentuk tersambung, juga pada draf 1/2.

Hasil: dataset/metadata.csv kolom `transkrip`, status_label = "terkoreksi", catatan + "sumber=draf1|draf2|ketik".
Cadangan metadata.csv dibuat sebelum penulisan pertama.

Pemakaian:
    python bench/koreksi_transkrip.py                       # memakai CSV hipotesis terbaru
    python bench/koreksi_transkrip.py --penutur R02
"""
import argparse
import csv
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import sounddevice as sd
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils import load_config  # noqa: E402

DRAF = ["faster:cuda:prompt", "openai:cuda:noprompt"]
UMUM = {"ruang", "ruangan", "sini", "sana", "mana", "situ", "posisi", "tempat", "dekat", "depan", "belakang", "samping",
        "kiri", "kanan", "lab", "laboratorium"}


def kata_tempat_domain(cfg):
    """Kata pertama tiap alias entity domain (+ kata tempat umum): dipakai mendeteksi 'ke'/'di' tersambung."""
    import re as _re
    import yaml
    d = yaml.safe_load((ROOT / cfg["nlu"]["domain_vocab"]).read_text(encoding="utf-8"))
    w = set(UMUM)
    for sec in d.values():
        if isinstance(sec, dict):
            for canon, al in sec.items():
                for a in [canon, *(al or [])]:
                    t = _re.sub(r"[^\w\s]", " ", str(a).lower()).split()
                    if t and len(t[0]) > 2:
                        w.add(t[0])
    return w


def kata_depan_sambung(text, kata):
    import re as _re
    low = text.lower()
    out = [t for t in _re.findall(r"\w+", low)
           if _re.match(r"^(ke|di)(\w+)$", t) and _re.match(r"^(ke|di)(\w+)$", t).group(2) in kata]
    out += [f"{x}-{y}" for x, y in _re.findall(r"\b(ke|di)-(\w+)", low) if y in kata]   # ke-trainer
    return out


def pisah_kata_depan(text, kata):
    import re as _re
    text = _re.sub(r"\b([KkDd][ei])-(\w+)", lambda m: f"{m.group(1)} {m.group(2)}" if m.group(2).lower() in kata else m.group(0), text)
    return _re.sub(r"\b([KkDd][ei])(\w+)\b", lambda m: f"{m.group(1)} {m.group(2)}" if m.group(2).lower() in kata else m.group(0), text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hipotesis", help="CSV dari bench/tes_asr.py (default: terbaru)")
    ap.add_argument("--penutur")
    ap.add_argument("--ulang", nargs="+", default=[], help="PENUTUR:ITEM yang dikoreksi ulang, mis. R02:S53 (label ikut dikosongkan)")
    a = ap.parse_args()
    cfg = load_config()
    droot = ROOT / cfg["dataset"]["out_skenario"]
    hp = Path(a.hipotesis) if a.hipotesis else max(droot.glob("asr_hipotesis_*.csv"), key=lambda p: p.stat().st_mtime)
    hyp = {(r["konfig"], r["penutur"], r["item_id"]): r["hipotesis"]
           for r in csv.DictReader(open(hp, encoding="utf-8"))}
    meta_p = droot / "metadata.csv"
    meta = list(csv.DictReader(open(meta_p, encoding="utf-8")))
    cols = list(meta[0].keys())
    ulang = {tuple(u.upper().split(":")) for u in a.ulang}
    if ulang:
        todo = [m for m in meta if (m["penutur"], m["item_id"]) in ulang]
    else:
        todo = [m for m in meta if m["mode"] == "skenario" and m["status_label"] not in ("terkoreksi", "final")
                and (not a.penutur or m["penutur"] == a.penutur.upper())]
    print(f"Draf dari {hp.name}. Belum dikoreksi: {len(todo)} / {len(meta)}")
    kata_tempat = kata_tempat_domain(cfg)
    backed = False
    for n, m in enumerate(todo, 1):
        x, sr = sf.read(droot / m["wav"], dtype="float32")
        d = [hyp.get((k, m["penutur"], m["item_id"]), "") for k in DRAF]
        print("=" * 70)
        print(f"[{n}/{len(todo)}] {m['penutur']}_{m['item_id']} ({m['formality']})  kartu: {m['tujuan']}")
        print(f"  draf 1: {d[0]}")
        print(f"  draf 2: {d[1]}")
        if m["transkrip"].strip() and ulang:
            print(f"  lama  : {m['transkrip']}")
        sd.play(x, sr)
        while True:
            c = input("  r=putar | 1 atau 2 = draf itu benar | ketik transkrip | s=lewati | q=keluar\n  > ").strip()
            if c.lower() == "r":
                sd.stop()
                sd.play(x, sr)
                continue
            if c not in ("1", "2") and c.lower() not in ("s", "q", "") and (
                    re.search(r"\d|/", c) or len(c.split()) < 2):
                # temuan 12 Nov: "1/2" tersimpan sebagai transkrip (R02_S53, R03_S02)
                if input(f"  Transkrip '{c}' tampak bukan kalimat (angka / '/' / satu kata). Simpan? (y/n) ").strip() != "y":
                    continue
            break
        sd.stop()
        if c.lower() == "q":
            break
        if c.lower() == "s" or not c:
            continue
        if c in ("1", "2"):
            text, src = d[int(c) - 1], f"draf{c}"
        else:
            text, src = c, "ketik"
        sambung = kata_depan_sambung(text, kata_tempat)
        if sambung:
            usul = pisah_kata_depan(text, kata_tempat)
            print(f"  PERHATIAN: kata depan tersambung {sambung}. Usulan EYD: {usul}")
            j = input("  Enter = pakai usulan | k = simpan apa adanya | atau ketik ulang transkrip\n  > ").strip()
            if j == "":
                text = usul
            elif j.lower() != "k":
                text, src = j, "ketik"
        if not backed:
            shutil.copy(meta_p, meta_p.with_name(f"metadata.bak_{datetime.now():%Y%m%d_%H%M%S}.csv"))
            backed = True
        m["transkrip"] = text
        if m["status_label"] == "final" or m.get("label_final_json", "").strip():
            m["label_final_json"] = ""          # transkrip berubah -> label harus dicek ulang
        m["status_label"] = "terkoreksi"
        m["catatan"] = ";".join(x for x in [m["catatan"], f"sumber={src}"] if x)
        tmp = meta_p.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(meta)
        tmp.replace(meta_p)
        print(f"  tersimpan: {text}")
    done = sum(m["status_label"] in ("terkoreksi", "final") for m in meta)
    print(f"\nTerkoreksi: {done} / {len(meta)}")


if __name__ == "__main__":
    main()
