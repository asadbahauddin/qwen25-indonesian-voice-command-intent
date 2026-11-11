"""F8 - Cek kebocoran data: kalimat dataset responden (set uji) tidak boleh sama/mirip dengan
pilot (set pengembangan), data latih IndoBERT, dan contoh few-shot di prompt Qwen.

Dibandingkan: transkrip terkoreksi dataset vs
  - bench/pilot_set.json (36 kalimat)
  - data/indobert_train.jsonl (data latih IndoBERT)
  - contoh "Perintah: ..." di prompt Qwen aktif (prompts/system_id.txt)
Ukuran: sama persis (setelah normalisasi huruf kecil + tanda baca) dan kemiripan Jaccard token.
Ambang "mirip": Jaccard >= 0.8 (ditetapkan sebelum dijalankan).

Laporan hanya memuat ID dan skor (kalimat responden tidak ditulis ke results/ karena repo publik).

    python bench/cek_kebocoran.py
"""
import csv
import io
import json
import re
import socket
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.nlu.base import norm_text  # noqa: E402
from src.utils import load_config  # noqa: E402

AMBANG = 0.8


def jac(a, b):
    a, b = set(a.split()), set(b.split())
    return len(a & b) / len(a | b) if a | b else 0.0


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    cfg = load_config()
    q = cfg["nlu"]["qwen"]
    sumber = {
        "pilot": [(i["id"], i["text"]) for i in json.load(open(ROOT / cfg["dataset"]["pilot"], encoding="utf-8"))["items"]],
        "latih_indobert": [(r["id"], r["text"]) for r in map(json.loads, open(ROOT / cfg["nlu"]["indobert"]["train_data"], encoding="utf-8"))],
        "prompt_qwen": [(f"contoh{k + 1}", t) for k, t in enumerate(re.findall(
            r"^Perintah:\s*(.+)$", (ROOT / q["prompts"][q["prompt_version"]]["file"]).read_text(encoding="utf-8"), re.M))],
    }
    sumber = {k: [(i, t, norm_text(t)) for i, t in v] for k, v in sumber.items()}
    meta = [m for m in csv.DictReader(open(ROOT / cfg["dataset"]["out_skenario"] / "metadata.csv", encoding="utf-8"))
            if m["status_label"] in ("terkoreksi", "final") and m["transkrip"].strip()]
    host, ts = socket.gethostname(), datetime.now().strftime("%Y%m%d_%H%M%S")
    L = [f"# Cek kebocoran data ({host}, {ts})", "",
         f"Dataset: {len(meta)} transkrip terkoreksi. Pembanding: " +
         ", ".join(f"{k} ({len(v)})" for k, v in sumber.items()) +
         f". Ambang mirip: Jaccard token ≥ {AMBANG} (ditetapkan sebelum dijalankan). Normalisasi: huruf kecil, tanpa tanda baca.", "",
         "| Pembanding | Sama persis | Mirip (≥ ambang) | Jaccard maks | Item dataset terdekat → sumber |", "|---|---|---|---|---|"]
    out = {"n_dataset": len(meta), "ambang": AMBANG, "sumber": {}}
    for k, src in sumber.items():
        best = []
        for m in meta:
            t = norm_text(m["transkrip"])
            j, sid, stext = max(((jac(t, s), i, raw) for i, raw, s in src), key=lambda x: x[0])
            best.append((j, f"{m['penutur']}_{m['item_id']}", sid, stext, t == norm_text(stext)))
        best.sort(reverse=True)
        same = [b for b in best if b[4]]
        mirip = [b for b in best if b[0] >= AMBANG]
        top = best[0]
        L.append(f"| {k} | {len(same)} | {len(mirip)} | {top[0]:.2f} | {top[1]} → {top[2]} \"{top[3]}\" |")
        out["sumber"][k] = {"n": len(src), "sama_persis": [b[1] for b in same],
                            "mirip": [{"item": b[1], "sumber": b[2], "jaccard": round(b[0], 3)} for b in mirip],
                            "jaccard_maks": round(top[0], 3)}
    L += ["", "Item yang mirip (ID dataset → ID sumber, Jaccard):", ""]
    for k, v in out["sumber"].items():
        L.append(f"- {k}: " + (", ".join(f"{x['item']}→{x['sumber']} ({x['jaccard']:.2f})" for x in v["mirip"]) or "tidak ada"))
    L += ["", "Catatan: kalimat sumber (pilot/latih/prompt) bersifat publik; kalimat responden tidak ditulis di sini.",
          "Kemiripan tinggi pada perintah sangat pendek (mis. \"robot cari pak kus\") bisa terjadi wajar karena kosakata "
          "domain terbatas; keputusan mengeluarkan item ditetapkan peneliti."]
    md = cfg["paths"]["results"] / f"kebocoran_{host}_{ts}.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    md.with_suffix(".json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(L))
    print("->", md.relative_to(ROOT))


if __name__ == "__main__":
    main()
