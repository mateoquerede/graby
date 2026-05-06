"""
Planner module

Uses Ollama AI to convert product names into optimized search queries
for supermarket shopping, maintaining exact quantities.
"""

import json
import re
import ollama

def extract_json(text):
    """
    Extrae el primer array JSON válido desde la respuesta del modelo.
    Sirve aunque Ollama agregue texto antes o después.
    """
    candidates = re.findall(r"\[[\s\S]*?\]", text)

    for candidate in candidates:
        try:
            data = json.loads(candidate)

            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            continue

    raise ValueError(f"No se encontró un JSON válido en la respuesta:\n{text}")


def validate_plan(data):
    """
    Valida que cada item tenga query y cantidad.
    Normaliza cantidad a int cuando sea posible.
    """
    if not isinstance(data, list):
        raise ValueError("El planner debe devolver una lista JSON")

    validated = []

    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"Item inválido: {item}")

        query = item.get("query")
        cantidad = item.get("cantidad")

        if not query:
            raise ValueError(f"Item sin query: {item}")

        if cantidad is None:
            raise ValueError(f"Item sin cantidad: {item}")

        validated.append({
            "query": str(query).strip(),
            "cantidad": int(float(cantidad))
        })

    return validated


def plan(productos):
    prompt = f"""
Convertí cada producto en una búsqueda de supermercado.

REGLAS OBLIGATORIAS:
- Devolvé SOLO JSON válido.
- No escribas explicaciones.
- No uses markdown.
- No uses ```json.
- No agregues texto antes ni después.
- Mantené la cantidad EXACTA.
- No cambies números.
- No agregues productos.
- No elimines productos.

FORMATO EXACTO:
[
  {{"query":"leche entera","cantidad":2}}
]

PRODUCTOS:
{json.dumps(productos, ensure_ascii=False)}
"""

    response = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "system",
                "content": "Sos un conversor estricto a JSON. Respondés únicamente JSON válido, sin texto adicional."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0,
            "top_p": 0.1
        }
    )

    raw = response["message"]["content"].strip()

    print("\n🧠 Respuesta planner:")
    print(raw)

    data = extract_json(raw)
    return validate_plan(data)