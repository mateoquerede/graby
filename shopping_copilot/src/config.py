"""
Configuration module.

Loads JSON config files from project root.
"""

import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

ROOT_DIR = Path(__file__).resolve().parents[2]

SHARED_DIR = ROOT_DIR / "shared"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_settings():
    return load_json(
        SHARED_DIR / "settings.json"
    )


def load_shopping_list():
    return load_json(
        PROJECT_DIR / "shopping_list.json"
    )


BLOCKED = load_json(
    PROJECT_DIR / "blocked.json"
)

RULES = load_json(
    PROJECT_DIR / "rules.json"
)