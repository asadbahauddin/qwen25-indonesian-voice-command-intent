"""Ekstraksi entity berbasis kamus + pemecahan klausa (dipakai rule-based dan IndoBERT).

- Entity dicari dengan pencocokan alias TERPANJANG lebih dulu, tanpa tumpang tindih,
  sehingga "ruangan pak umam" menjadi room (bukan person "pak umam"),
  dan "ruang asisten" menjadi room (bukan person "asisten").
- Klausa dipecah pada kata penghubung (lalu, kemudian, habis itu, ...) dari config/keywords_id.yaml.
"""
import re

from .base import ENTITY_FIELDS, norm_text


class EntityExtractor:
    def __init__(self, domain, keywords):
        self.domain = domain
        pats = []
        for field in ENTITY_FIELDS:
            for alias, canon in domain.alias[field].items():
                pats.append((alias, field, canon))
        pats.sort(key=lambda p: -len(p[0]))          # alias terpanjang dulu
        self.patterns = [(re.compile(rf"(?<!\w){re.escape(a)}(?!\w)"), f, c) for a, f, c in pats]
        conn = sorted(keywords["connectors"], key=len, reverse=True)
        self.split_re = re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, conn)) + r")(?!\w)")
        self.pronoun_re = re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, keywords["pronouns"])) + r")(?!\w)")

    def extract(self, text):
        """Return ({field: kanonik|None}, daftar (posisi, field, kanonik)) dari teks."""
        t = norm_text(text)
        used = [False] * len(t)
        found = []
        for rx, field, canon in self.patterns:
            for m in rx.finditer(t):
                if not any(used[m.start():m.end()]):
                    for i in range(m.start(), m.end()):
                        used[i] = True
                    found.append((m.start(), field, canon))
        found.sort()
        ents = {f: None for f in ENTITY_FIELDS}
        for _, field, canon in found:
            if ents[field] is None:                   # ambil kemunculan pertama per field
                ents[field] = canon
        return ents, found

    def has_pronoun(self, text):
        return bool(self.pronoun_re.search(norm_text(text)))

    def split_clauses(self, text):
        """Pecah teks ternormalisasi pada kata penghubung; buang klausa kosong."""
        parts = [p.strip() for p in self.split_re.split(norm_text(text))]
        return [p for p in parts if p]
