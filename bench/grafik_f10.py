"""F10 - Grafik untuk laporan, artikel, dan poster. Semua angka dibaca dari JSON hasil (bukan diketik).

    python bench/grafik_f10.py results/eval_dataset_<..>.json results/analisis_dataset_<..>.json
Keluaran: luaran/gambar/*.png (300 dpi) + luaran/gambar/sumber.txt (berkas sumber tiap grafik).
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "luaran" / "gambar"
MET = ["qwen", "rule", "indobert"]
NAMA = {"qwen": "Qwen2.5 1.5B", "rule": "Rule-based", "indobert": "IndoBERT"}
WARNA = {"qwen": "#4C72B0", "rule": "#DD8452", "indobert": "#55A868"}
INTENTS = ["navigate_room", "navigate_object", "find_person", "deliver_document", "combined_command", "general_command"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


LANG = {"cur": "id"}


def num(v, d=1):
    t = f"{v:.{d}f}"
    return t.replace(".", ",") if LANG["cur"] == "id" else t


def comma_axes(fig):
    if LANG["cur"] != "id":
        return
    from matplotlib.ticker import FuncFormatter
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            if axis.get_major_formatter().__class__.__name__ == "ScalarFormatter":
                axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))


def bar_label(ax, bars, fmt=None):
    for b in bars:
        ax.annotate(num(b.get_height()), (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha="center", va="bottom", fontsize=8, xytext=(0, 2), textcoords="offset points")


def akurasi(ev, lang):
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4), sharey=True)
    lab = {"id": (["Teks", "Rekaman utuh", "VAD → Whisper"], "Intent Accuracy (%)", "Exact Match (%)"),
           "en": (["Text", "Full audio", "VAD → Whisper"], "Intent accuracy (%)", "Exact match (%)")}[lang]
    for ax, metr, judul in zip(axes, ["intent_acc", "exact_match"], lab[1:]):
        x = np.arange(3)
        for k, m in enumerate(MET):
            v = [ev["akurasi"][f"gpu/{mk}/{m}"]["semua"][metr] * 100 for mk in ("teks", "utuh", "vad")]
            bar_label(ax, ax.bar(x + (k - 1) * 0.26, v, 0.26, label=NAMA[m], color=WARNA[m]))
        ax.set_xticks(x, lab[0]); ax.set_title(judul); ax.set_ylim(0, 108)
    h, l_ = axes[0].get_legend_handles_labels()
    fig.legend(h, l_, loc="upper center", ncol=3, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    return fig


def formalitas(ev, lang):
    F = ["formal", "semi-formal", "informal"]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4), sharey=True)
    tt = {"id": ("Masukan teks", "Masukan VAD → Whisper", "Intent Accuracy (%)"), "en": ("Text input", "VAD → Whisper input", "Intent accuracy (%)")}[lang]
    for ax, mk, judul in zip(axes, ["teks", "vad"], tt[:2]):
        x = np.arange(3)
        for k, m in enumerate(MET):
            v = [ev["akurasi"][f"gpu/{mk}/{m}"][f"formality={f}"]["intent_acc"] * 100 for f in F]
            bar_label(ax, ax.bar(x + (k - 1) * 0.26, v, 0.26, label=NAMA[m], color=WARNA[m]))
        ax.set_xticks(x, F); ax.set_title(judul); ax.set_ylim(0, 108)
    axes[0].set_ylabel(tt[2])
    h, l_ = axes[0].get_legend_handles_labels()
    fig.legend(h, l_, loc="upper center", ncol=3, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    return fig


def latency(ev, lang):
    fig, ax = plt.subplots(figsize=(7, 2.8))
    plat = [("gpu", "Laptop GPU"), ("cpu", "Laptop CPU")]
    komp = [("t_vad", "VAD", "#8C8C8C"), ("t_asr", "Whisper", "#C44E52"), ("t_nlu", "Qwen2.5", "#4C72B0")]
    for i, (d, nm) in enumerate(plat):
        lt = ev["latency"][f"{d}/vad/qwen"]
        left = 0
        for c, lab, col in komp:
            w = lt[c]["mean"]
            ax.barh(i, w, left=left, color=col, label=lab if i == 0 else None)
            left += w
        ax.annotate(f"{num(left, 2)} s", (left, i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=9)
    ax.set_yticks(range(2), [p[1] for p in plat]); ax.invert_yaxis()
    ax.set_xlabel({"id": "Waktu komputasi rata-rata per ujaran (s), n = 162", "en": "Mean computation time per utterance (s), n = 162"}[lang])
    ax.set_xlim(0, left * 1.15)
    ax.legend(ncol=3, fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout()
    return fig


def f1_intent(an, lang):
    res = an["per_intent"]["gpu/teks"]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    x = np.arange(len(INTENTS))
    for k, m in enumerate(MET):
        ax.bar(x + (k - 1) * 0.26, [res[m][i]["f1"] for i in INTENTS], 0.26, label=NAMA[m], color=WARNA[m])
    ax.set_xticks(x, [i.replace("_", "_\n", 1) for i in INTENTS], fontsize=8)
    ax.set_ylabel({"id": "F1 (masukan teks)", "en": "F1 (text input)"}[lang]); ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout()
    return fig


def confusion(ev, m, lang):
    c = ev["confusion"][f"gpu/teks/{m}"]
    lab, M = c["label"], np.array(c["matriks"])
    keep = [k for k, l in enumerate(lab) if l != "INVALID" or M[:, k].sum() > 0]
    M = M[np.ix_(keep, keep)]
    short = [lab[k].replace("navigate_", "nav_").replace("_command", "").replace("deliver_document", "deliver") for k in keep]
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    ax.imshow(M, cmap="Blues")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if M[i, j]:
                ax.text(j, i, M[i, j], ha="center", va="center", fontsize=8, color="white" if M[i, j] > M.max() / 2 else "black")
    ax.set_xticks(range(len(short)), short, rotation=45, ha="right", fontsize=8); ax.set_yticks(range(len(short)), short, fontsize=8)
    ax.set_xlabel({"id": "Prediksi", "en": "Predicted"}[lang]); ax.set_ylabel({"id": "Label", "en": "Gold"}[lang])
    ax.set_title(f"{NAMA[m]} ({'teks' if lang == 'id' else 'text'}, n = {M.sum()})", fontsize=9)
    fig.tight_layout()
    return fig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("eval_json")
    ap.add_argument("analisis_json")
    a = ap.parse_args()
    ev = json.load(open(a.eval_json, encoding="utf-8"))
    an = json.load(open(a.analisis_json, encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for lang in ("id", "en"):
        LANG["cur"] = lang
        for name, fig in [("akurasi", akurasi(ev, lang)), ("formalitas", formalitas(ev, lang)), ("latency", latency(ev, lang)),
                          ("f1_intent", f1_intent(an, lang)), ("cm_qwen", confusion(ev, "qwen", lang)),
                          ("cm_indobert", confusion(ev, "indobert", lang))]:
            p = OUT / f"{name}_{lang}.png"
            comma_axes(fig)
            fig.savefig(p, dpi=300); plt.close(fig); made.append(p.name)
    (OUT / "sumber.txt").write_text(f"Sumber: {Path(a.eval_json).name}, {Path(a.analisis_json).name}\n" + "\n".join(made) + "\n", encoding="utf-8")
    print("\n".join(made))


if __name__ == "__main__":
    main()
