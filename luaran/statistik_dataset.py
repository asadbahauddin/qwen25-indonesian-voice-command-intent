"""Statistik dataset dari dataset/metadata.csv + responden.csv untuk data card (Lampiran 7 & Dokumentasi/F8_data_card.md).

    python luaran/statistik_dataset.py <keluaran.json>
Keluaran berisi agregat + satu contoh baris (R01_S31); kalimat responden lain tidak ditulis.
"""
import collections
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
r = list(csv.DictReader(open(ROOT / "dataset" / "metadata.csv", encoding="utf-8")))
resp = list(csv.DictReader(open(ROOT / "dataset" / "responden.csv", encoding="utf-8")))
lab = [json.loads(x["label_final_json"]) for x in r]
d = [float(x["durasi_s"]) for x in r]
w = [len(x["transkrip"].split()) for x in r]
ent = collections.Counter(k for L in lab for k in ("room", "object", "person", "document") if L.get(k))
steps = collections.Counter(len(L["steps"] or []) for L in lab if L["intent"] == "combined_command")
src = collections.Counter(([p for p in x["catatan"].split(";") if p.startswith("sumber=")] or ["sumber=?"])[-1].split("(")[0]
                          for x in r)
ex = next(x for x in r if x["penutur"] == "R01" and x["item_id"] == "S31")
out = {
    "n": len(r), "status": dict(collections.Counter(x["status_label"] for x in r)),
    "intent": dict(collections.Counter(L["intent"] for L in lab)),
    "formalitas": dict(collections.Counter(x["formality"] for x in r)),
    "penutur": dict(collections.Counter(x["penutur"] for x in r)),
    "responden": [{k: v[k] for k in ("penutur", "usia", "jenis_kelamin", "bahasa_ibu", "tanggal")} for v in resp],
    "durasi": {"total_menit": sum(d) / 60, "mean": st.mean(d), "sd": st.stdev(d), "min": min(d), "max": max(d)},
    "kata": {"mean": st.mean(w), "sd": st.stdev(w), "min": min(w), "max": max(w), "total": sum(w)},
    "entity_terisi": dict(ent), "steps_combined": {str(k): v for k, v in steps.items()},
    "label_sama_target": sum(json.loads(x["target_json"]) == L for x, L in zip(r, lab)),
    "sumber_transkrip": dict(src), "kolom": list(r[0].keys()),
    "contoh": {k: ex[k] for k in ("penutur", "item_id", "formality", "tujuan", "wav", "durasi_s", "transkrip", "label_final_json", "status_label")},
}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: out[k] for k in ("n", "durasi", "kata", "entity_terisi", "label_sama_target", "sumber_transkrip")}, ensure_ascii=False))
