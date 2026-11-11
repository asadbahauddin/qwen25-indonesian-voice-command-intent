"""F8 - Pembuatan kartu skenario untuk perekaman dataset responden (kalimat bebas).

Setiap kartu berisi TUJUAN perintah (intent + entity target + gaya bahasa), BUKAN kalimat,
sehingga responden menyusun kalimatnya sendiri (perintah kalimat bebas).
- 6 intent x 9 kartu = 54 kartu; formalitas seimbang 18/18/18 (3 responden x 54 = 162 ujaran).
- Entity diputar agar semua ruangan/benda/orang/dokumen di config/domain_id.yaml muncul.
- `target` = label yang DIHARAPKAN; label akhir ditetapkan setelah transkrip diperiksa
  (responden bisa saja menyimpang dari kartu).

Pemakaian:
    python bench/buat_skenario.py      -> bench/skenario_dataset.json
"""
import collections
import json
import sys
from itertools import cycle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.nlu.base import ENTITY_FIELDS, INTENTS, Domain, validate_command  # noqa: E402
from src.utils import load_config  # noqa: E402

PER_INTENT = 9
FORMS = ["formal", "semi-formal", "informal"]
GAYA = {
    "formal": "FORMAL: sopan dan baku, seperti berbicara kepada dosen.",
    "semi-formal": "SEMI-FORMAL: sopan tetapi santai, seperti kepada kakak tingkat.",
    "informal": "INFORMAL: santai seperti kepada teman dekat, boleh bahasa gaul/daerah.",
}
UMUM = [  # (deskripsi tujuan, tanpa memberi kalimat jadi)
    "Robot harus BERHENTI bergerak.",
    "Robot harus MENUNGGU sebentar di tempatnya.",
    "Robot harus KEMBALI ke posisi awalnya.",
    "Robot harus MAJU sedikit.",
    "Robot harus MUNDUR sedikit.",
    "Robot harus berjalan LEBIH PELAN.",
    "Robot harus PUTAR BALIK.",
    "Robot harus DIAM di tempat dan tidak bergerak.",
    "Robot harus berjalan LEBIH CEPAT.",
]
UMUM_SINGKAT = ["berhenti", "menunggu sebentar", "kembali ke posisi awal", "maju sedikit", "mundur sedikit",
                "berjalan lebih pelan", "putar balik", "diam di tempat", "berjalan lebih cepat"]


def up(s):
    return s.upper()


def empty():
    return {f: None for f in ENTITY_FIELDS}


def main():
    cfg = load_config()
    d = Domain(ROOT / cfg["nlu"]["domain_vocab"])
    rooms, objs = cycle(d.canonical["room"]), cycle(d.canonical["object"])
    persons = cycle([p for p in d.canonical["person"]])
    docs = cycle(d.canonical["document"])
    umum = cycle(range(len(UMUM)))

    def step(intent):
        """Return (deskripsi singkat, label langkah)."""
        if intent == "navigate_room":
            r = next(rooms)
            return f"pergi ke {up(r)}", {"intent": intent, **empty(), "room": r}
        if intent == "navigate_object":
            o = next(objs)
            return f"pergi ke {up(o)}", {"intent": intent, **empty(), "object": o}
        if intent == "find_person":
            p = next(persons)
            return f"mencari {up(p)}", {"intent": intent, **empty(), "person": p}
        if intent == "deliver_document":
            doc = next(docs)
            if step.toggle:
                p = next(persons)
                step.toggle = False
                return f"mengantar {up(doc)} kepada {up(p)}", {"intent": intent, **empty(), "document": doc, "person": p}
            r = next(rooms)
            step.toggle = True
            return f"mengantar {up(doc)} ke {up(r)}", {"intent": intent, **empty(), "document": doc, "room": r}
        if intent == "general_command":
            k = next(umum)
            return UMUM_SINGKAT[k], {"intent": intent, **empty()}
        raise ValueError(intent)
    step.toggle = True

    combos = [("navigate_room", "find_person"), ("navigate_object", "navigate_room"), ("find_person", "PRONOUN"),
              ("navigate_room", "deliver_document"), ("navigate_object", "find_person"),
              ("navigate_room", "general_command"), ("find_person", "navigate_object"),
              ("deliver_document", "navigate_room"), ("navigate_object", "general_command")]
    cards, n = [], 0
    for ii, intent in enumerate(INTENTS):
        for k in range(PER_INTENT):
            form = FORMS[(k + ii) % 3]
            n += 1
            if intent == "combined_command":
                a, b = combos[k]
                d1, s1 = step(a)
                if b == "PRONOUN":
                    doc = next(docs)
                    d2 = f"mengantar {up(doc)} kepada orang yang sama (boleh pakai kata 'beliau'/'dia')"
                    s2 = {"intent": "deliver_document", **empty(), "document": doc, "person": s1["person"]}
                else:
                    d2, s2 = step(b)
                tujuan = f"DUA tindakan berurutan dalam SATU perintah: (1) robot {d1}; (2) robot {d2}."
                target = {"intent": intent, **empty(), "steps": [s1, s2]}
            elif intent == "general_command":
                desc, lab = step(intent)
                tujuan = UMUM[UMUM_SINGKAT.index(desc)]
                target = {**lab, "steps": None}
            else:
                desc, lab = step(intent)
                tujuan = f"Minta robot {desc}."
                target = {**lab, "steps": None}
            ok, err = validate_command(target)
            assert ok, (tujuan, err)
            cards.append({"id": f"S{n:02d}", "formality": form, "tujuan": tujuan, "gaya": GAYA[form],
                          "target": target})

    out = ROOT / "bench" / "skenario_dataset.json"
    meta = {"nama": "Kartu skenario dataset responden (kalimat bebas)", "versi": "v2", "tanggal": "2026-11-11",
            "jumlah": len(cards), "desain": "6 intent x 9 kartu, formalitas 18/18/18",
            "catatan": "Responden menyusun kalimat sendiri. 'target' = label yang diharapkan; label akhir "
                       "ditetapkan setelah transkrip diperiksa."}
    out.write_text(json.dumps({"_meta": meta, "items": cards}, indent=2, ensure_ascii=False), encoding="utf-8")
    c = collections.Counter(x["formality"] for x in cards)
    used = collections.defaultdict(set)
    for x in cards:
        for s in (x["target"]["steps"] or [x["target"]]):
            for f in ENTITY_FIELDS:
                if s.get(f):
                    used[f].add(s[f])
    print(f"{len(cards)} kartu -> {out}")
    print("formalitas:", dict(c))
    for f in ENTITY_FIELDS:
        miss = set(d.canonical[f]) - used[f]
        print(f"  {f:8s}: {len(used[f])}/{len(d.canonical[f])} tercakup", f"(tidak: {sorted(miss)})" if miss else "")
    for x in cards[:2] + cards[32:34] + cards[40:41]:
        print(f"  {x['id']} [{x['formality']}] {x['tujuan']}")


if __name__ == "__main__":
    main()
