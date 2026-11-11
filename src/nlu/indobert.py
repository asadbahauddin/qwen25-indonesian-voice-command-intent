"""Baseline supervised: IndoBERT fine-tuned (klasifikasi intent) + kamus entity bersama.

- Intent kalimat diprediksi oleh IndoBERT (models/indobert_intent, hasil bench/latih_indobert.py).
- Entity diambil dengan EntityExtractor yang sama dengan rule-based (config/domain_id.yaml),
  lalu hanya field yang relevan dengan intent yang diisi.
- Bila intent = combined_command: kalimat dipecah per klausa (kata penghubung), tiap klausa
  diklasifikasi IndoBERT (dibatasi ke intent non-combined) + entity per klausa.

Uji cepat:
    python -m src.nlu.indobert "Tolong antarkan surat izin ke Pak Umam"
"""
import json
import logging
import sys
import time
from pathlib import Path

import torch
import yaml
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .base import ENTITY_FIELDS, Domain, NLUMethod, normalize_command, validate_command
from .entities import EntityExtractor

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
FIELD_FOR = {"navigate_room": ["room"], "navigate_object": ["object"], "find_person": ["person"],
             "general_command": []}


class IndoBertNLU(NLUMethod):
    name = "indobert"

    def __init__(self, cfg, domain=None):
        ncfg = cfg["nlu"]
        c = ncfg["indobert"]
        self.domain = domain or Domain(ROOT / ncfg["domain_vocab"])
        kw = yaml.safe_load((ROOT / ncfg["rule"]["keywords"]).read_text(encoding="utf-8"))
        self.ex = EntityExtractor(self.domain, kw)
        dev = c["device"] if c["device"] != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
        self.device = torch.device(dev)
        self.max_len = c["max_len"]
        mdir = ROOT / c["model_dir"]
        if not (mdir / "config.json").exists():
            raise FileNotFoundError(f"Model IndoBERT belum ada di {mdir}. Jalankan: python bench/latih_indobert.py")
        t0 = time.perf_counter()
        self.tok = AutoTokenizer.from_pretrained(str(mdir))
        self.model = AutoModelForSequenceClassification.from_pretrained(str(mdir)).to(self.device).eval()
        self.id2label = {int(k): v for k, v in self.model.config.id2label.items()}
        self.non_combined = [i for i, lab in self.id2label.items() if lab != "combined_command"]
        self.load_s = time.perf_counter() - t0
        log.info("IndoBertNLU: %s di %s, muat %.2f s", mdir.name, self.device, self.load_s)

    @torch.no_grad()
    def _logits(self, texts):
        enc = self.tok(texts, padding=True, truncation=True, max_length=self.max_len, return_tensors="pt")
        enc = {k: v.to(self.device) for k, v in enc.items()}
        return self.model(**enc).logits.float().cpu()

    def _step(self, intent, clause, last_person=None):
        ents, _ = self.ex.extract(clause)
        if ents["person"] is None and last_person and self.ex.has_pronoun(clause):
            ents["person"] = last_person
        step = {"intent": intent, **{f: None for f in ENTITY_FIELDS}}
        if intent == "deliver_document":
            step["document"] = ents["document"]
            if ents["person"]:
                step["person"] = ents["person"]
            else:
                step["room"] = ents["room"]
        else:
            for f in FIELD_FOR.get(intent, []):
                step[f] = ents[f]
        return step

    def warmup(self):
        t0 = time.perf_counter()
        self._logits(["berhenti"])
        return {"warmup_s": time.perf_counter() - t0, "load_s": self.load_s}

    def predict(self, text):
        t0 = time.perf_counter()
        logits = self._logits([text])[0]
        probs = torch.softmax(logits, -1)
        intent = self.id2label[int(probs.argmax())]
        info = {"method": self.name, "device": str(self.device), "json_valid": True,
                "intent_prob": round(float(probs.max()), 4)}
        if intent == "combined_command":
            clauses = self.ex.split_clauses(text)
            steps, last = [], None
            if clauses:
                cl = self._logits(clauses)[:, self.non_combined]
                for clause, row in zip(clauses, cl):
                    sub = self.id2label[self.non_combined[int(row.argmax())]]
                    s = self._step(sub, clause, last)
                    last = s["person"] or last
                    steps.append(s)
            cmd = {"intent": intent, **{f: None for f in ENTITY_FIELDS}, "steps": steps or None}
        else:
            cmd = {**self._step(intent, text), "steps": None}
        cmd = normalize_command(cmd, self.domain)
        if self.device.type == "cuda":
            torch.cuda.synchronize()
        info["t_nlu"] = time.perf_counter() - t0
        info["schema_valid"], err = validate_command(cmd)
        info["error"] = None if info["schema_valid"] else f"schema: {err}"
        return cmd, info


def _main():
    sys.path.insert(0, str(ROOT))
    from src.utils import load_config
    cfg = load_config()
    text = " ".join(sys.argv[1:]) or "Tolong antarkan surat izin ke Pak Umam"
    nlu = IndoBertNLU(cfg)
    print("warm-up:", nlu.warmup())
    cmd, info = nlu.predict(text)
    print("Perintah:", text)
    print("JSON    :", json.dumps(cmd, ensure_ascii=False))
    print("info    :", json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in info.items()},
                                  ensure_ascii=False))


if __name__ == "__main__":
    _main()
