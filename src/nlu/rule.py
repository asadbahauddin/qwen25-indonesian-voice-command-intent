"""Baseline bawah: rule-based keyword matching.

Alur per kalimat:
1. Pecah menjadi klausa pada kata penghubung (config/keywords_id.yaml: connectors).
2. Tiap klausa: ambil entity dari kamus (src/nlu/entities.py), lalu tentukan intent
   dengan urutan aturan tetap (lihat `classify_clause`).
3. >= 2 klausa yang menghasilkan tindakan -> combined_command dengan steps; kata ganti
   (beliau/dia) diisi orang dari klausa sebelumnya.

Uji cepat:
    python -m src.nlu.rule "Cari Pak Kus, terus antar laporan praktikum ke beliau"
"""
import json
import logging
import re
import sys
import time
from pathlib import Path

import yaml

from .base import ENTITY_FIELDS, Domain, NLUMethod, norm_text, normalize_command, validate_command
from .entities import EntityExtractor

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


def _kw_regex(words):
    words = sorted(words, key=len, reverse=True)
    return re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, words)) + r")(?!\w)")


class RuleNLU(NLUMethod):
    name = "rule"

    def __init__(self, cfg, domain=None):
        ncfg = cfg["nlu"]
        self.domain = domain or Domain(ROOT / ncfg["domain_vocab"])
        kw_path = ROOT / ncfg["rule"]["keywords"]
        self.kw = yaml.safe_load(kw_path.read_text(encoding="utf-8"))
        self.version = self.kw.get("version")
        self.ex = EntityExtractor(self.domain, self.kw)
        ik = self.kw["intent_keywords"]
        self.re_deliver = _kw_regex(ik["deliver_document"])
        self.re_find = _kw_regex(ik["find_person"])
        self.re_general = _kw_regex(ik["general_command"])
        log.info("RuleNLU: kamus %s (%s)", kw_path.name, self.version)

    def classify_clause(self, clause, last_person=None):
        """Return dict langkah {intent, room, object, person, document} atau None bila kosong."""
        ents, _ = self.ex.extract(clause)
        if ents["person"] is None and last_person and self.ex.has_pronoun(clause):
            ents["person"] = last_person
        t = norm_text(clause)
        step = {"intent": None, **{f: None for f in ENTITY_FIELDS}}
        if ents["document"] and (self.re_deliver.search(t) or ents["person"] or ents["room"]):
            step.update(intent="deliver_document", document=ents["document"])
            if ents["person"]:
                step["person"] = ents["person"]
            else:
                step["room"] = ents["room"]
        elif ents["person"] and self.re_find.search(t):
            step.update(intent="find_person", person=ents["person"])
        elif ents["room"]:
            step.update(intent="navigate_room", room=ents["room"])
        elif ents["object"]:
            step.update(intent="navigate_object", object=ents["object"])
        elif ents["person"]:
            step.update(intent="find_person", person=ents["person"])
        elif self.re_general.search(t) or t:
            step["intent"] = "general_command"
        else:
            return None
        return step

    def parse(self, text):
        clauses = self.ex.split_clauses(text)
        pairs, last_person = [], None
        for c in clauses:
            s = self.classify_clause(c, last_person)
            if s is None:
                continue
            last_person = s["person"] or last_person
            pairs.append((c, s))
        # klausa general tanpa kata kunci general (sisa kata seperti "ya", "dong") tidak dihitung
        if len(pairs) > 1:
            pairs = [(c, s) for c, s in pairs
                     if s["intent"] != "general_command" or self.re_general.search(c)]
        steps = [s for _, s in pairs]
        if len(steps) >= 2:
            return {"intent": "combined_command", **{f: None for f in ENTITY_FIELDS}, "steps": steps}
        if steps:
            return {**steps[0], "steps": None}
        return {"intent": "general_command", **{f: None for f in ENTITY_FIELDS}, "steps": None}

    def predict(self, text):
        t0 = time.perf_counter()
        cmd = normalize_command(self.parse(text), self.domain)
        ok, err = validate_command(cmd)
        return cmd, {"method": self.name, "keywords_version": self.version, "json_valid": True,
                     "schema_valid": ok, "error": None if ok else f"schema: {err}",
                     "t_nlu": time.perf_counter() - t0}


def _main():
    sys.path.insert(0, str(ROOT))
    from src.utils import load_config
    cfg = load_config()
    text = " ".join(sys.argv[1:]) or "Cari Pak Kus, terus antar laporan praktikum ke beliau"
    cmd, info = RuleNLU(cfg).predict(text)
    print("Perintah:", text)
    print("JSON    :", json.dumps(cmd, ensure_ascii=False))
    print("info    :", json.dumps(info, ensure_ascii=False, default=str))


if __name__ == "__main__":
    _main()
