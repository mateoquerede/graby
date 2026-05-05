"""
Planner module

Uses Ollama AI to convert product names into optimized search queries
for supermarket shopping, maintaining exact quantities.
"""

import ollama
import json
import re


def extract_json(text):
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise Exception("No JSON returned")
    return json.loads(match.group(0))


def plan(productos):

    prompt = f"""
Convertí cada producto en una búsqueda de supermercado.

IMPORTANTE:
- Mantener cantidad EXACTA
- NO cambiar números
- SOLO devolver JSON

Formato:

[
  {{"query":"leche entera","cantidad":2}}
]

Productos:
{json.dumps(productos, ensure_ascii=False)}
"""

    r = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )

    raw = r["message"]["content"]

    print(raw)

    return extract_json(raw)