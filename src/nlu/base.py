"""Antarmuka bersama untuk ketiga metode NLU (Qwen2.5, rule-based, IndoBERT).

Setiap metode mengimplementasikan:
    predict(text) -> (command: dict | None, info: dict)
`command` selalu mengikuti skema perintah robot (lihat COMMAND_SCHEMA) setelah normalisasi;
`info` minimal berisi: method, json_valid, t_nlu (detik), error.

Normalisasi entity (huruf kecil, tanda baca, alias -> nama kanonik dari config/domain_id.yaml)
diterapkan SAMA untuk semua metode, agar Exact Match membandingkan makna, bukan ejaan.
"""
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

INTENTS = ["navigate_room", "navigate_object", "find_person", "deliver_document",
           "combined_command", "general_command"]
STEP_INTENTS = [i for i in INTENTS if i != "combined_command"]
ENTITY_FIELDS = ["room", "object", "person", "document"]
# nama field skema -> nama bagian di domain_id.yaml
DOMAIN_SECTION = {"room": "rooms", "object": "objects", "person": "persons", "document": "documents"}

_nullable_str = {"type": ["string", "null"]}
_step = {
    "type": "object",
    "properties": {"intent": {"type": "string", "enum": STEP_INTENTS},
                   **{f: _nullable_str for f in ENTITY_FIELDS}},
    "required": ["intent", *ENTITY_FIELDS],
    "additionalProperties": False,
}
COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": INTENTS},
        **{f: _nullable_str for f in ENTITY_FIELDS},
        "steps": {"anyOf": [{"type": "null"}, {"type": "array", "items": _step, "minItems": 1}]},
    },
    "required": ["intent", *ENTITY_FIELDS, "steps"],
    "additionalProperties": False,
}
_validator = Draft202012Validator(COMMAND_SCHEMA)


def validate_command(obj):
    """Return (valid: bool, pesan galat pertama atau None)."""
    errs = sorted(_validator.iter_errors(obj), key=lambda e: list(e.path))
    if not errs:
        return True, None
    e = errs[0]
    return False, f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}"


def parse_json(raw):
    """Ambil objek JSON dari teks keluaran model (toleran terhadap ```json ... ```)."""
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", s, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def norm_text(s):
    """Huruf kecil, buang tanda baca (kecuali tanda hubung di tengah kata), rapikan spasi."""
    s = s.lower()
    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"(?<!\w)-|-(?!\w)", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class Domain:
    """Kosakata domain: alias -> nilai kanonik per field entity."""

    def __init__(self, path):
        self.path = Path(path)
        data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self.canonical = {}   # field -> [nilai kanonik]
        self.alias = {}       # field -> {alias ternormalisasi: kanonik}
        for field, sec in DOMAIN_SECTION.items():
            entries = data.get(sec, {}) or {}
            self.canonical[field] = list(entries)
            amap = {}
            for canon, aliases in entries.items():
                for a in [canon, *(aliases or [])]:
                    amap[norm_text(a)] = canon
            self.alias[field] = amap

    def canon(self, field, value):
        """Petakan nilai entity ke nama kanonik bila dikenal; selain itu kembalikan teks ternormalisasi."""
        if value is None:
            return None
        v = norm_text(str(value))
        if not v or v in {"null", "none", "tidak ada", "-"}:
            return None
        amap = self.alias[field]
        if v in amap:
            return amap[v]
        # contoh: "ruangan bu vivi" vs alias "ruang bu vivi"; "laporan praktikum ini" -> buang kata penunjuk
        v2 = re.sub(r"\b(ini|itu|tersebut|yang|sana|sini)\b", " ", v)
        v2 = re.sub(r"\s+", " ", v2).strip()
        return amap.get(v2, v2 or None)


def normalize_command(obj, domain):
    """Lengkapi field yang hilang dengan null dan petakan entity ke nama kanonik.
    Tidak mengubah intent/struktur (kesalahan model tetap terlihat)."""
    if not isinstance(obj, dict):
        return obj
    out = {"intent": obj.get("intent")}
    for f in ENTITY_FIELDS:
        out[f] = domain.canon(f, obj.get(f))
    steps = obj.get("steps")
    if isinstance(steps, list):
        out["steps"] = [normalize_command({**s, "steps": None}, domain) if isinstance(s, dict) else s
                        for s in steps]
        for s in out["steps"]:
            if isinstance(s, dict):
                s.pop("steps", None)
        if not out["steps"]:
            out["steps"] = None
    else:
        out["steps"] = steps
    return out


class NLUMethod(ABC):
    """Kelas dasar. Subkelas wajib mengisi `name` dan `predict`."""

    name = "base"

    def warmup(self):
        """Opsional: muat model sebelum pengukuran latency. Return info dict."""
        return {}

    @abstractmethod
    def predict(self, text):
        """Return (command dict ternormalisasi atau None, info dict)."""
