from pathlib import Path
import json

ROOT_DIR = Path(__file__).resolve().parents[1]
SHARED_DIR = ROOT_DIR / "shared"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_settings():
    return load_json(SHARED_DIR / "settings.json")

def load_consumption_rules():
    return load_json(SHARED_DIR / "grocy" / "consumption_rules.json")