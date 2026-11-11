"""F4b - Pembuatan data latih IndoBERT (sintetis, berbasis templat) -> data/indobert_train.jsonl

- 6 intent x 50 kalimat = 300, seimbang formalitas (formal / semi-formal / informal).
- Nilai entity diambil dari config/domain_id.yaml; bentuk ucapan memakai alias (variasi),
  label memakai nama kanonik.
- Seed tetap (bisa dibuat ulang persis sama).
- ANTI-LEAKAGE: kalimat yang (setelah normalisasi) sama dengan set pilot atau contoh
  few-shot di prompt Qwen dibuang, lalu diverifikasi ulang.

Pemakaian:
    python bench/buat_data_latih.py
"""
import collections
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.nlu.base import ENTITY_FIELDS, Domain, norm_text, validate_command  # noqa: E402
from src.utils import load_config  # noqa: E402

SEED = 42
PER_INTENT = 50
FORMS = ["formal", "semi-formal", "informal"]

T = {
    "navigate_room": {
        "formal": ["Silakan pergi ke {room}.", "Mohon menuju {room}.", "Robot, harap bergerak ke {room}.",
                   "Mohon segera menuju {room}.", "Bergeraklah menuju {room}.", "Silakan berjalan ke {room}."],
        "semi-formal": ["Tolong pergi ke {room} ya.", "Bisa ke {room} sekarang?", "Coba jalan ke {room}.",
                        "Robot, ke {room} ya.", "Ayo ke {room}.", "Tolong arahkan robot ke {room}."],
        "informal": ["Cus ke {room}.", "Gas ke {room} dong.", "Ke {room} sono.", "Jalan ke {room} gih.",
                     "Meluncur ke {room}, buruan.", "Buruan ke {room}."],
    },
    "navigate_object": {
        "formal": ["Silakan menuju {object}.", "Mohon bergerak ke dekat {object}.", "Harap menghampiri {object}.",
                   "Robot, silakan mendekati {object}.", "Mohon pergi ke lokasi {object}.",
                   "Silakan berhenti di samping {object}."],
        "semi-formal": ["Tolong ke {object} ya.", "Coba hampiri {object}.", "Bisa ke dekat {object}?",
                        "Robot, datangi {object} sebentar.", "Tolong dekati {object}.", "Coba jalan ke {object}."],
        "informal": ["Samperin {object} dong.", "Ke {object} bentar.", "Deketin {object} gih.",
                     "Meluncur ke {object}.", "Gas ke {object}.", "Ke arah {object} sono."],
    },
    "find_person": {
        "formal": ["Mohon carikan {person}.", "Silakan temukan {person}.", "Tolong cari tahu keberadaan {person}.",
                   "Harap mencari {person}.", "Mohon panggilkan {person}.", "Robot, silakan mencari {person}."],
        "semi-formal": ["Tolong cari {person} ya.", "Bisa carikan {person}?", "Coba temukan {person}.",
                        "{Person} ada di mana? Tolong cari.", "Tolong panggil {person}.", "Coba cari {person} dulu."],
        "informal": ["Cariin {person} dong.", "{Person} mana sih, cari gih.", "Temuin {person} buruan.",
                     "Cari {person} bentar.", "Panggilin {person} dong.", "Eh, {person} di mana? Cariin."],
    },
    "deliver_document": {
        "formal": ["Mohon antarkan {document} ini kepada {person}.", "Silakan serahkan {document} ke {room}.",
                   "Harap kirimkan {document} kepada {person}.", "Mohon bawa {document} ini ke {room}.",
                   "Silakan berikan {document} kepada {person}.", "Mohon antarkan {document} ke {room}."],
        "semi-formal": ["Tolong bawa {document} ini ke {person} ya.", "Tolong anter {document} ke {room}.",
                        "Bisa kirim {document} ke {person}?", "Coba kasih {document} ini ke {person}.",
                        "Tolong antar {document} ke {room} ya.", "Bisa bawakan {document} ke {person}?"],
        "informal": ["Anterin {document} ke {person} dong.", "{Document} ini bawa ke {room} gih.",
                     "Kasihin {document} ke {person}, cepet.", "Bawain {document} ke {room} ya.",
                     "Kirimin {document} ke {person} dong.", "Anter {document} ke {room} bentar."],
    },
    "general_command": {
        "formal": ["Mohon berhenti.", "Silakan tunggu di tempat.", "Harap kembali ke posisi semula.",
                   "Mohon kurangi kecepatan.", "Silakan maju perlahan.", "Mohon putar balik.",
                   "Harap diam di tempat.", "Silakan mundur sedikit."],
        "semi-formal": ["Tolong berhenti dulu ya.", "Coba tunggu sebentar.", "Tolong mundur sedikit.",
                        "Coba maju pelan-pelan.", "Tolong balik ke posisi awal.", "Robot, diam dulu ya.",
                        "Pelan sedikit ya.", "Tolong putar badan."],
        "informal": ["Udah, stop.", "Bentar, tunggu dulu.", "Mundur dikit dong.", "Maju lagi gih.",
                     "Balik sono.", "Diem di situ.", "Pelan-pelan napa.", "Jangan gerak dulu."],
    },
}
GEN_PREFIX = {"formal": ["", "Robot, ", "Baik, "], "semi-formal": ["", "Robot, ", "Oke, "], "informal": ["", "Eh, ", "Woy, "]}

# combined_command: potongan klausa per intent langkah dan penghubung per formalitas
CLAUSE = {
    "navigate_room": {"formal": "menuju {room}", "semi-formal": "ke {room}", "informal": "ke {room}"},
    "navigate_object": {"formal": "menuju {object}", "semi-formal": "ke {object}", "informal": "samperin {object}"},
    "find_person": {"formal": "carikan {person}", "semi-formal": "cari {person}", "informal": "cariin {person}"},
    "deliver_document": {"formal": "antarkan {document} kepada {person}", "semi-formal": "bawa {document} ke {person}",
                         "informal": "anterin {document} ke {person}"},
    "general_command": {"formal": "kembali ke posisi awal", "semi-formal": "tunggu di sana",
                        "informal": "balik lagi"},
}
CONNECT = {"formal": [", kemudian ", ", lalu ", ", setelah itu "],
           "semi-formal": [" dulu, habis itu ", ", terus ", ", lalu "],
           "informal": [" bentar, abis itu ", ", trus ", " dulu, terus "]}
PREFIX = {"formal": ["Silakan ", "Mohon "], "semi-formal": ["Tolong ", "Coba "], "informal": ["", "Eh robot, "]}
SUFFIX = {"formal": ".", "semi-formal": " ya.", "informal": " dong."}
PAIRS = [("navigate_room", "find_person"), ("navigate_object", "navigate_room"),
         ("find_person", "deliver_pron"), ("navigate_room", "deliver_document"),
         ("navigate_object", "find_person"), ("navigate_room", "general_command"),
         ("find_person", "navigate_object"), ("deliver_document", "navigate_room")]
PRON = {"formal": "beliau", "semi-formal": "beliau", "informal": "dia"}

ACRONYM = {"plc", "cnc", "rl", "ta", "pc"}
TITLES = {"pak", "bu", "bapak", "ibu", "mas", "mbak"}


def surface(alias):
    """Huruf besar yang wajar: gelar + nama dikapitalisasi, singkatan huruf besar."""
    w = alias.split()
    out = []
    for i, x in enumerate(w):
        if x in ACRONYM:
            out.append(x.upper())
        elif x in TITLES or (i > 0 and w[i - 1] in {"pak", "bu", "bapak", "ibu"}):
            out.append(x.capitalize())
        else:
            out.append(x)
    return " ".join(out)


def cap_first(s):
    return s[:1].upper() + s[1:]


class Gen:
    def __init__(self, domain, rng):
        self.d, self.rng = domain, rng
        # alias per field (bentuk ucapan) -> kanonik; buang alias yang terlalu umum
        self.forms = {}
        for f in ENTITY_FIELDS:
            pairs = []
            for alias, canon in domain.alias[f].items():
                if f == "person" and alias in {"asisten"}:
                    continue
                if f == "document" and alias in {"surat", "jadwal"}:
                    continue
                pairs.append((alias, canon))
            self.forms[f] = pairs

    def ent(self, f):
        alias, canon = self.rng.choice(self.forms[f])
        return surface(alias), canon

    def fill(self, tmpl):
        label = {f: None for f in ENTITY_FIELDS}
        out = tmpl
        for f in ENTITY_FIELDS:
            for key in ("{" + f + "}", "{" + f.capitalize() + "}"):
                if key in out:
                    s, c = self.ent(f)
                    out = out.replace(key, s if key.islower() or not key[1].isupper() else cap_first(s))
                    label[f] = c
        return cap_first(out), label

    def simple(self, intent, form):
        if intent == "general_command":
            t = self.rng.choice(T[intent][form])
            p = self.rng.choice(GEN_PREFIX[form])
            text = p + (t[0].lower() + t[1:] if p else t)
            return cap_first(text), {f: None for f in ENTITY_FIELDS}
        return self.fill(self.rng.choice(T[intent][form]))

    def step(self, intent, form, person=None):
        txt, lab = self.fill(CLAUSE[intent][form])
        if person is not None and lab.get("person"):
            pass
        return txt[0].lower() + txt[1:], {"intent": intent, **lab}

    def combined(self, form):
        a, b = self.rng.choice(PAIRS)
        t1, s1 = self.step(a, form)
        if b == "deliver_pron":
            doc_s, doc_c = self.ent("document")
            t2 = CLAUSE["deliver_document"][form].replace("{document}", doc_s).replace("{person}", PRON[form])
            s2 = {"intent": "deliver_document", "room": None, "object": None, "person": s1["person"],
                  "document": doc_c}
        else:
            t2, s2 = self.step(b, form)
        text = self.rng.choice(PREFIX[form]) + t1 + self.rng.choice(CONNECT[form]) + t2 + SUFFIX[form]
        text = re.sub(r"\s+", " ", text).strip()
        return cap_first(text), {f: None for f in ENTITY_FIELDS}, [s1, s2]


def main():
    cfg = load_config()
    domain = Domain(ROOT / cfg["nlu"]["domain_vocab"])
    rng = random.Random(SEED)
    g = Gen(domain, rng)

    pilot = json.load(open(ROOT / "bench/pilot_set.json", encoding="utf-8"))["items"]
    prompt_ex = re.findall(r"^Perintah: (.+)$", (ROOT / cfg["nlu"]["qwen"]["system_prompt"])
                           .read_text(encoding="utf-8"), re.M)
    forbidden = {norm_text(x["text"]) for x in pilot} | {norm_text(e) for e in prompt_ex}

    rows, seen, dropped = [], set(), collections.Counter()
    from src.nlu.base import INTENTS
    for intent in INTENTS:
        for k, form in enumerate(FORMS):
            target = PER_INTENT // 3 + (1 if k < PER_INTENT % 3 else 0)
            got, tries = 0, 0
            while got < target:
                tries += 1
                if tries > 5000:
                    raise RuntimeError(f"Kombinasi templat habis untuk {intent}/{form} ({got}/{target})")
                if intent == "combined_command":
                    text, ents, steps = g.combined(form)
                    label = {"intent": intent, **ents, "steps": steps}
                else:
                    text, ents = g.simple(intent, form)
                    if intent == "deliver_document":   # tujuan: orang ATAU ruangan
                        ents = {**ents}
                    label = {"intent": intent, **ents, "steps": None}
                key = norm_text(text)
                if key in forbidden:
                    dropped["sama_dengan_pilot/prompt"] += 1
                    continue
                if key in seen:
                    dropped["duplikat"] += 1
                    continue
                ok, err = validate_command(label)
                if not ok:
                    raise ValueError(f"Label tidak valid: {text} -> {err}")
                seen.add(key)
                rows.append({"id": f"T{len(rows) + 1:03d}", "text": text, "formality": form, "label": label,
                             "source": "sintetis-templat", "seed": SEED})
                got += 1

    # verifikasi akhir anti-leakage
    leak = [r["text"] for r in rows if norm_text(r["text"]) in forbidden]
    assert not leak, leak
    out = ROOT / "data" / "indobert_train.jsonl"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    cnt = collections.Counter((r["label"]["intent"], r["formality"]) for r in rows)
    print(f"Tulis {len(rows)} kalimat -> {out}")
    print("Per intent x formalitas:")
    for intent in INTENTS:
        print(f"  {intent:18s}", {f: cnt[(intent, f)] for f in FORMS})
    print("Dibuang:", dict(dropped))
    print("Kebocoran ke pilot/prompt: 0 (terverifikasi)")


if __name__ == "__main__":
    main()
