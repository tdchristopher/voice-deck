import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def load_config(path=None):
    """Load config.yaml (falls back to config.example.yaml) and .env secrets."""
    load_dotenv(ROOT / ".env")
    path = Path(path or os.environ.get("VOICEDECK_CONFIG", ROOT / "config.yaml"))
    if not path.exists():
        path = ROOT / "config.example.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    cfg["_root"] = str(ROOT)
    return cfg


def resolve_path(cfg, p):
    """Make a config path absolute relative to the repo root."""
    p = Path(p)
    return p if p.is_absolute() else Path(cfg.get("_root", ROOT)) / p
