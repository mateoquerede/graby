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

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
MAX_AI_PROMPT_CHARS = int(os.environ.get("MAX_AI_PROMPT_CHARS", "500"))
MAX_AI_ITEMS = int(os.environ.get("MAX_AI_ITEMS", "20"))
MAX_AI_QUANTITY = int(os.environ.get("MAX_AI_QUANTITY", "50"))
MAX_AI_CANDIDATES = int(os.environ.get("MAX_AI_CANDIDATES", "25"))
OLLAMA_NUM_PREDICT = int(os.environ.get("OLLAMA_NUM_PREDICT", "256"))
