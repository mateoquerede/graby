"""
Configuration for shopping automation helpers used by the SaaS worker.

Credentials are never loaded from disk: the API/worker pass them per job.
"""

import json
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def load_json(path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def is_debug_enabled():
    return os.environ.get("GRABY_DEBUG", "").lower() in {"1", "true", "yes", "on"}


def debug_print(*args, **kwargs):
    if is_debug_enabled():
        print(*args, **kwargs)


BLOCKED = load_json(PROJECT_DIR / "blocked.json", default={})
RULES = load_json(PROJECT_DIR / "rules.json", default={})
