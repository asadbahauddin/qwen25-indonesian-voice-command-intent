"""Metode utama: Qwen2.5 1.5B (Q4_K_M) via Ollama HTTP API, prompt engineering + JSON schema.

Keluaran dibatasi dengan structured output Ollama (`format` = skema versi `nlu.qwen.schema_version`)
bila `nlu.qwen.use_schema: true`, sehingga model hanya bisa menghasilkan JSON yang sesuai skema.

Uji cepat dari terminal:
    python -m src.nlu.qwen "Tolong antarkan surat izin ke Pak Umam"
"""
import hashlib
import json
import logging
import sys
import time
from pathlib import Path

import requests

from .base import SCHEMAS, Domain, with_plan_field, NLUMethod, normalize_command, parse_json, validate_command

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
NS = 1e9


def render_prompt(template, domain):
    rep = {"<<ROOMS>>": "room", "<<OBJECTS>>": "object", "<<PERSONS>>": "person", "<<DOCUMENTS>>": "document"}
    for tag, field in rep.items():
        template = template.replace(tag, ", ".join(domain.canonical[field]))
    return template


class QwenNLU(NLUMethod):
    name = "qwen"

    def __init__(self, cfg, domain=None):
        ncfg = cfg["nlu"]
        self.q = ncfg["qwen"]
        self.domain = domain or Domain(ROOT / ncfg["domain_vocab"])
        self.prompt_version = self.q["prompt_version"]
        pcfg = self.q["prompts"][self.prompt_version]
        tmpl = (ROOT / pcfg["file"]).read_text(encoding="utf-8")
        self.system_prompt = render_prompt(tmpl, self.domain)
        self.plan_field = bool(pcfg.get("plan_field"))
        self.schema_version = self.q.get("schema_version", "v2")
        schema = SCHEMAS[self.schema_version]
        self.gen_schema = with_plan_field(schema) if self.plan_field else schema
        self.prompt_sha = hashlib.sha256(self.system_prompt.encode("utf-8")).hexdigest()[:12]
        self.url = self.q["host"].rstrip("/") + "/api/chat"
        self.session = requests.Session()
        self.num_gpu = self.q.get("num_gpu")
        log.info("QwenNLU: model=%s prompt=%s (sha %s, %d karakter) schema=%s (%s)",
                 self.q["model"], self.prompt_version, self.prompt_sha, len(self.system_prompt),
                 self.q["use_schema"], self.schema_version)

    def _payload(self, text):
        p = {
            "model": self.q["model"],
            "stream": False,
            "keep_alive": self.q["keep_alive"],
            "messages": [{"role": "system", "content": self.system_prompt},
                         {"role": "user", "content": f"Perintah: {text}"}],
            "options": {"temperature": self.q["temperature"], "seed": self.q["seed"],
                        "num_ctx": self.q["num_ctx"], "num_predict": self.q["num_predict"]},
        }
        if self.num_gpu is not None:        # 0 = paksa CPU (skenario laptop CPU)
            p["options"]["num_gpu"] = self.num_gpu
        p["format"] = self.gen_schema if self.q["use_schema"] else "json"
        return p

    def warmup(self):
        """Muat model ke memori (load_duration) agar tidak ikut terhitung di latency perintah pertama."""
        cmd, info = self.predict("Berhenti.")
        return {"warmup_s": info["t_nlu"], "load_s": info.get("load_s")}

    def predict(self, text):
        info = {"method": self.name, "model": self.q["model"], "prompt_version": self.prompt_version,
                "prompt_sha": self.prompt_sha, "schema_version": self.schema_version, "json_valid": False, "schema_valid": False,
                "error": None, "raw": None}
        t0 = time.perf_counter()
        try:
            r = self.session.post(self.url, json=self._payload(text), timeout=self.q["timeout_s"])
            r.raise_for_status()
            d = r.json()
        except (requests.RequestException, ValueError) as e:
            info["t_nlu"] = time.perf_counter() - t0
            info["error"] = f"ollama: {e}"
            log.error("Qwen gagal: %s", e)
            return None, info
        info["t_nlu"] = time.perf_counter() - t0

        # rincian waktu dari Ollama (nanodetik -> detik)
        ev_n, ev_d = d.get("eval_count") or 0, d.get("eval_duration") or 0
        info.update({
            "total_s": (d.get("total_duration") or 0) / NS,
            "load_s": (d.get("load_duration") or 0) / NS,
            "prompt_eval_s": (d.get("prompt_eval_duration") or 0) / NS,
            "prompt_tokens": d.get("prompt_eval_count") or 0,
            "eval_s": ev_d / NS,
            "eval_tokens": ev_n,
            "tokens_per_s": ev_n / (ev_d / NS) if ev_d else None,
        })
        raw = (d.get("message") or {}).get("content", "")
        info["raw"] = raw
        try:
            obj = parse_json(raw)
            info["json_valid"] = True
        except (json.JSONDecodeError, TypeError) as e:
            info["error"] = f"json: {e}"
            return None, info
        if self.plan_field and isinstance(obj, dict):
            info["tindakan"] = obj.pop("tindakan", None)
        info["schema_valid"], err = validate_command(obj)
        cmd = normalize_command(obj, self.domain)
        if not info["schema_valid"]:
            info["error"] = f"schema: {err}"
        return cmd, info


def _main():
    sys.path.insert(0, str(ROOT))
    from src.utils import load_config, setup_logging
    cfg = load_config()
    setup_logging(cfg, "qwen")
    text = " ".join(sys.argv[1:]) or "Tolong antarkan surat izin ke Pak Umam"
    nlu = QwenNLU(cfg)
    print("warm-up:", nlu.warmup())
    cmd, info = nlu.predict(text)
    print("Perintah:", text)
    print("JSON    :", json.dumps(cmd, ensure_ascii=False))
    print("info    :", json.dumps({k: (round(v, 3) if isinstance(v, float) else v)
                                   for k, v in info.items() if k != "raw"}, ensure_ascii=False))


if __name__ == "__main__":
    _main()
