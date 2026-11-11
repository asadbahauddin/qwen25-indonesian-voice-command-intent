"""Utilitas bersama: memuat config.yaml dan menyiapkan logging ke file."""
import logging
import socket
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"


def load_config(path=None):
    """Baca YAML; path di bagian `paths` diubah menjadi absolut relatif ke file config."""
    path = Path(path) if path else DEFAULT_CONFIG
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    base = path.resolve().parent
    for key, val in cfg.get("paths", {}).items():
        p = Path(val)
        cfg["paths"][key] = p if p.is_absolute() else base / p
        cfg["paths"][key].mkdir(parents=True, exist_ok=True)
    cfg["_config_path"] = path.resolve()
    return cfg


def setup_logging(cfg, name):
    """Logging ke logs/<name>_<host>_<tanggal>.log (+ konsol bila diaktifkan)."""
    log_cfg = cfg["logging"]
    log_file = cfg["paths"]["logs"] / f"{name}_{socket.gethostname()}_{datetime.now():%Y%m%d}.log"
    handlers = [logging.FileHandler(log_file, encoding="utf-8")]
    if log_cfg.get("console", True):
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=getattr(logging, log_cfg["level"].upper()),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    logging.getLogger(name).info("Log file: %s | config: %s", log_file, cfg["_config_path"])
    return log_file
