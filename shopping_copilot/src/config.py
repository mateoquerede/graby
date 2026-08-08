"""
Configuration module.

Loads JSON config files from project root.
"""

import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

ROOT_DIR = Path(__file__).resolve().parents[2]

SHARED_DIR = ROOT_DIR / "shared"
SHOPPING_LIST_PATH = PROJECT_DIR / "shopping_list.json"


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_settings():
    return load_json(
        SHARED_DIR / "settings.json"
    )


def load_shopping_list():
    return load_json(
        SHOPPING_LIST_PATH
    )


def save_shopping_list(items):
    with open(SHOPPING_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


BLOCKED = load_json(
    PROJECT_DIR / "blocked.json"
)

RULES = load_json(
    PROJECT_DIR / "rules.json"
)