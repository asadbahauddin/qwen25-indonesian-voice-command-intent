"""F8 - Pelabelan final dataset responden (intent + entity) dari transkrip terkoreksi.

Prinsip (lihat Dokumentasi/F8_label.md):
  - Label = apa yang BENAR-BENAR DIUCAPKAN (transkrip terkoreksi), bukan isi kartu.
    Entity tidak disebut -> null; menyebut entity lain -> entity itu; dua tindakan -> combined_command.
  - Draf label = TARGET KARTU (bukan keluaran Qwen/rule/IndoBERT, agar label tidak berpihak ke satu metode).
  - Petunjuk "tidak ditemukan di transkrip" memakai kamus alias domain hanya untuk menarik perhatian penilai;
    keputusan tetap pada penilai.

Perintah per item:
  Enter        draf (target kartu) sudah sesuai dengan yang diucapkan -> dipakai
  e            ubah per field (Enter = tetap, '-' = null)
  j            tempel JSON lengkap (wajib untuk mengubah steps combined_command)
  s            lewati          q   keluar (progres tersimpan)

Hasil: dataset/metadata.csv kolom label_final_json (ternormalisasi, lolos skema v2), status_label = "final",
catatan + "label=target|ubah|json". Cadangan metadata dibuat sebelum penulisan pertama.

Pemakaian:
    python bench/label_dataset.py                 # semua item terkoreksi yang belum berlabel
    python bench/label_dataset.py --penutur R01
    python bench/label_dataset.py --ulang R01:S05 # ubah label item yang sudah final
"""
import argparse
import csv
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.nlu.base import (ENTITY_FIELDS, INTENTS, Domain, norm_text, normalize_command,  # noqa: E402
                          validate_command)
from src.utils import load_config  # noqa: E402

RELEVAN = {"navigate_room": ["room"], "navigate_object": ["object"], "find_person": ["person"],
           "deliver_document": ["document", "person", "room"], "general_command": [], "combined_command": []}


def aliases_of(domain):
    rev = {f: {} for f in ENTITY_FIELDS}
    for f in ENTITY_FIELDS:
        for al, canon in domain.alias[f].items():
            rev[f].setdefault(canon, []).append(al)
    return rev


def missing_entities(label, transcript, rev):
    """Entity di label yang TIDAK satu pun aliasnya muncul di transkrip (petunjuk, bukan keputusan)."""
    t = " " + norm_text(transcript) + " "
    out = []
    for step in [label, *(label.get("steps") or [])]:
        for f in ENTITY_FIELDS:
            v = step.get(f)
            if v and not any(f" {a} " in t for a in rev[f].get(v, [norm_text(v)])):
                out.append(f"{f}={v}")
    return out


def show(lbl):
    return json.dumps(lbl, ensure_ascii=False)


def edit_fields(lbl, domain):
    it = input(f"    intent [{lbl['intent']}] ({', '.join(INTENTS)}): ").strip() or lbl["intent"]
    if it not in INTENTS:
        print("    intent tidak dikenal, dibatalkan.")
        return None
    if it == "combined_command":
        print("    combined_command: pakai 'j' untuk menempel JSON dengan steps.")
        return None
    new = {"intent": it, **{f: None for f in ENTITY_FIELDS}, "steps": None}
    for f in RELEVAN[it]:
        cur = lbl.get(f) if lbl.get("intent") == it or f in RELEVAN.get(lbl.get("intent"), []) else None
        opts = ", ".join(domain.canonical[f])
        v = input(f"    {f} [{cur}] (pilihan: {opts}; '-' = null): ").strip()
        new[f] = None if v == "-" else (v or cur)
    return new


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--penutur")
    ap.add_argument("--ulang", nargs="+", default=[], help="PENUTUR:ITEM yang labelnya diubah lagi, mis. R01:S05")
    a = ap.parse_args()
    cfg = load_config()
    domain = Domain(ROOT / cfg["nlu"]["domain_vocab"])
    rev = aliases_of(domain)
    droot = ROOT / cfg["dataset"]["out_skenario"]
    meta_p = droot / "metadata.csv"
    meta = list(csv.DictReader(open(meta_p, encoding="utf-8")))
    cols = list(meta[0].keys())
    ulang = {tuple(u.upper().split(":")) for u in a.ulang}
    if ulang:
        todo = [m for m in meta if (m["penutur"], m["item_id"]) in ulang]
    else:
        todo = [m for m in meta if m["mode"] == "skenario" and m["status_label"] == "terkoreksi"
                and not m["label_final_json"].strip() and (not a.penutur or m["penutur"] == a.penutur.upper())]
    n_tk = sum(m["status_label"] in ("terkoreksi", "final") for m in meta)
    print(f"Transkrip terkoreksi: {n_tk}/{len(meta)}. Akan dilabel: {len(todo)}. "
          f"Sudah final: {sum(m['status_label'] == 'final' for m in meta)}.")
    backed = False
    for n, m in enumerate(todo, 1):
        target = normalize_command(json.loads(m["target_json"]), domain)
        draf = normalize_command(json.loads(m["label_final_json"]), domain) if m["label_final_json"].strip() else target
        print("=" * 78)
        print(f"[{n}/{len(todo)}] {m['penutur']} {m['item_id']} ({m['formality']})")
        print(f"  KARTU     : {m['tujuan']}")
        print(f"  TRANSKRIP : {m['transkrip']}")
        print(f"  DRAF      : {show(draf)}")
        miss = missing_entities(draf, m["transkrip"], rev)
        if miss:
            print(f"  PERHATIAN : tidak ditemukan di transkrip -> {', '.join(miss)} (cek: tidak disebut / sebutan lain?)")
        while True:
            c = input("  Enter = sesuai | e = ubah | j = JSON | s = lewati | q = keluar > ").strip()
            if c == "q":
                print("Keluar. Progres tersimpan.")
                return
            if c == "s":
                lbl = None
                break
            if c == "":
                lbl, src = draf, "target" if draf == target else "lama"
            elif c == "e":
                lbl, src = edit_fields(draf, domain), "ubah"
                if lbl is None:
                    continue
            elif c == "j":
                try:
                    lbl, src = json.loads(input("    JSON: ")), "json"
                except json.JSONDecodeError as e:
                    print(f"    JSON tidak valid: {e}")
                    continue
            else:
                print("  perintah tidak dikenal.")
                continue
            lbl = normalize_command(lbl, domain)
            ok, err = validate_command(lbl)
            if not ok:
                print(f"    Tidak lolos skema v2: {err}. Ulangi.")
                continue
            asing = [f"{f}={s[f]}" for s in [lbl, *(lbl.get("steps") or [])] for f in ENTITY_FIELDS
                     if s.get(f) and s[f] not in domain.canonical[f]]
            if asing and input(f"    Nilai di luar kamus domain: {', '.join(asing)}. Tetap simpan? (y/n) ").strip() != "y":
                continue
            break
        if lbl is None:
            continue
        if not backed:
            shutil.copy(meta_p, droot / f"metadata.bak_{datetime.now():%Y%m%d_%H%M%S}.csv")
            backed = True
        m["label_final_json"] = json.dumps(lbl, ensure_ascii=False)
        m["status_label"] = "final"
        m["catatan"] = re.sub(r";?label=\w+", "", m.get("catatan", "")) + f";label={src}"
        with open(meta_p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(meta)
        print(f"  tersimpan ({src}): {show(lbl)}")
    print(f"Selesai. Final: {sum(x['status_label'] == 'final' for x in meta)}/{len(meta)}")


if __name__ == "__main__":
    main()
