"""
Configuration module

Loads configuration data from JSON files.
"""

import json

with open("../bloqueados.json", "r", encoding="utf-8") as f:
    BLOQUEADOS = json.load(f)

with open("../rules.json", "r", encoding="utf-8") as f:
    RULES = json.load(f)