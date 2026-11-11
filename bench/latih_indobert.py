"""F4b - Fine-tuning IndoBERT (indobenchmark/indobert-base-p1) untuk klasifikasi intent.

- Data: data/indobert_train.jsonl (300 kalimat sintetis, 6 intent).
- Split stratified train/val (nlu.indobert.val_ratio). Val hanya untuk memilih epoch terbaik;
  data UJI adalah set pilot (F6) dan dataset responden (F9), keduanya tidak pernah dilihat di sini.
- Loop PyTorch sederhana: AdamW + linear warmup/decay, mixed precision (fp16) bila CUDA.
- Model terbaik (akurasi val tertinggi, seri -> loss val terendah) disimpan ke nlu.indobert.model_dir.
- Riwayat training -> results/indobert_train_<host>_<waktu>.json

Pemakaian:
    python bench/latih_indobert.py
"""
import json
import logging
import random
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.nlu.base import INTENTS  # noqa: E402
from src.utils import load_config, setup_logging  # noqa: E402

log = logging.getLogger("latih_indobert")


def set_seed(s):
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)
    torch.cuda.manual_seed_all(s)


def batches(enc, labels, idx, bs, shuffle, rng):
    idx = list(idx)
    if shuffle:
        rng.shuffle(idx)
    for i in range(0, len(idx), bs):
        b = idx[i:i + bs]
        yield {k: v[b] for k, v in enc.items()}, labels[b]


@torch.no_grad()
def evaluate(model, enc, labels, idx, bs, device, amp):
    model.eval()
    preds, losses = [], []
    for x, y in batches(enc, labels, idx, bs, False, None):
        x = {k: v.to(device) for k, v in x.items()}
        y = y.to(device)
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp):
            out = model(**x, labels=y)
        losses.append(out.loss.item() * len(y))
        preds += out.logits.argmax(-1).tolist()
    y_true = labels[list(idx)].tolist()
    return {"loss": sum(losses) / len(idx), "acc": accuracy_score(y_true, preds),
            "f1_macro": f1_score(y_true, preds, average="macro")}


def main():
    cfg = load_config()
    setup_logging(cfg, "latih_indobert")
    c = cfg["nlu"]["indobert"]
    set_seed(c["seed"])
    rng = random.Random(c["seed"])
    dev_name = c["device"] if c["device"] != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(dev_name)
    amp = device.type == "cuda"

    rows = [json.loads(line) for line in open(ROOT / c["train_data"], encoding="utf-8")]
    texts = [r["text"] for r in rows]
    label2id = {lab: i for i, lab in enumerate(INTENTS)}
    labels = torch.tensor([label2id[r["label"]["intent"]] for r in rows])
    idx_tr, idx_va = train_test_split(np.arange(len(rows)), test_size=c["val_ratio"], random_state=c["seed"],
                                      stratify=labels.numpy())
    log.info("Data: %d kalimat (train %d, val %d), device=%s, amp=%s", len(rows), len(idx_tr), len(idx_va),
             device, amp)

    base = str(ROOT / c["base_model"])
    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForSequenceClassification.from_pretrained(
        base, num_labels=len(INTENTS), id2label={i: lab for lab, i in label2id.items()}, label2id=label2id
    ).to(device)
    enc = tok(texts, padding="max_length", truncation=True, max_length=c["max_len"], return_tensors="pt")
    n_trunc = sum(len(tok(t)["input_ids"]) > c["max_len"] for t in texts)

    steps_per_epoch = (len(idx_tr) + c["batch_size"] - 1) // c["batch_size"]
    total = steps_per_epoch * c["epochs"]
    no_decay = ["bias", "LayerNorm.weight"]
    groups = [{"params": [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
               "weight_decay": c["weight_decay"]},
              {"params": [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
               "weight_decay": 0.0}]
    opt = torch.optim.AdamW(groups, lr=c["lr"])
    sched = get_linear_schedule_with_warmup(opt, int(c["warmup_ratio"] * total), total)
    scaler = torch.amp.GradScaler(device.type, enabled=amp)

    hist, best, best_state = [], None, None
    t_start = time.perf_counter()
    for ep in range(1, c["epochs"] + 1):
        model.train()
        t0, tr_loss = time.perf_counter(), 0.0
        for x, y in batches(enc, labels, idx_tr, c["batch_size"], True, rng):
            x = {k: v.to(device) for k, v in x.items()}
            y = y.to(device)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp):
                loss = model(**x, labels=y).loss
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            tr_loss += loss.item() * len(y)
        va = evaluate(model, enc, labels, idx_va, c["batch_size"], device, amp)
        rec = {"epoch": ep, "train_loss": tr_loss / len(idx_tr), "val_loss": va["loss"], "val_acc": va["acc"],
               "val_f1_macro": va["f1_macro"], "detik": time.perf_counter() - t0}
        hist.append(rec)
        print(f"epoch {ep}: train_loss {rec['train_loss']:.4f} | val_loss {va['loss']:.4f} | "
              f"val_acc {va['acc']:.4f} | val_f1 {va['f1_macro']:.4f} | {rec['detik']:.1f} s", flush=True)
        if best is None or (va["acc"], -va["loss"]) > (best["val_acc"], -best["val_loss"]):
            best = rec
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    out_dir = ROOT / c["model_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)
    host, stamp = socket.gethostname(), datetime.now().strftime("%Y%m%d_%H%M%S")
    meta = {"host": host, "waktu": stamp, "base_model": c["base_model"], "device": str(device),
            "gpu": torch.cuda.get_device_name(0) if amp else None, "torch": torch.__version__,
            "config": c, "n_total": len(rows), "n_train": len(idx_tr), "n_val": len(idx_va),
            "kalimat_terpotong_max_len": int(n_trunc), "label2id": label2id,
            "epoch_terbaik": best["epoch"], "terbaik": best, "riwayat": hist,
            "durasi_total_s": time.perf_counter() - t_start,
            "catatan": "val diambil dari data latih sintetis; bukan hasil uji penelitian"}
    (out_dir / "training_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    res = cfg["paths"]["results"] / f"indobert_train_{host}_{stamp}.json"
    res.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nEpoch terbaik {best['epoch']}: val_acc {best['val_acc']:.4f}, val_f1 {best['val_f1_macro']:.4f}")
    print(f"Model -> {out_dir}\nRiwayat -> {res}")


if __name__ == "__main__":
    main()
