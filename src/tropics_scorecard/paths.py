"""Project paths. Everything downloaded or derived lives under data/, which git ignores."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
TABLES = DATA / "tables"
CONFIG = ROOT / "config" / "study.yaml"


def load_config() -> dict:
    import yaml

    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
