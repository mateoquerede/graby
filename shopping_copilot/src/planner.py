"""
Planner module

Uses Ollama AI to convert product names into optimized search queries
for supermarket shopping, maintaining exact quantities.
"""

import json
import re
import ollama
from shopping_copilot.src.config import debug_print, OLLAMA_MODEL


def singularize_spanish_query(query):
    """
    Best-effort singular normalization for product queries.
    Keeps phrase structure, singularizes simple plural tokens.
    """
    tokens = re.split(r"(\W+)", query.strip())
    normalized = []

    for token in tokens:
        if not token or re.fullmatch(r"\W+", token):
            normalized.append(token)
            continue

        lower = token.lower()

        if lower.endswith("ces") and len(lower) > 4:
            # luces -> luz, nueces -> nuez
            normalized.append(token[:-3] + "z")
            continue

        if lower.endswith(("as", "es", "is", "os", "us")) and len(lower) > 3:
            normalized.append(token[:-1])
            continue

        normalized.append(token)

    return "".join(normalized).strip()

def extract_json(text):
    """
    Extract the first valid JSON array from the model response.
    Works even if Ollama adds text before or after.
    """
    candidates = re.findall(r"\[[\s\S]*?\]", text)

    for candidate in candidates:
        try:
            data = json.loads(candidate)

            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            continue

    raise ValueError(f"No valid JSON array found in response:\n{text}")


def validate_plan(data):
    """
    Validate that each item has query and quantity.
    Normalize quantity to int when possible.
    """
    if not isinstance(data, list):
        raise ValueError("The planner must return a JSON list")

    validated = []

    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid item: {item}")

        query = item.get("query")
        quantity = item.get("quantity")

        if not query:
            raise ValueError(f"Missing query in item: {item}")

        if quantity is None:
            raise ValueError(f"Missing quantity in item: {item}")

        normalized_query = singularize_spanish_query(
            str(query).strip()
        )

        validated.append({
            "query": normalized_query,
            "quantity": int(float(quantity))
        })

    return validated


def plan(products):
    if not products:
        return []

    # If tasks are already in normalized shape, avoid a second AI pass.
    if isinstance(products, list) and all(
        isinstance(item, dict)
        and "query" in item
        and "quantity" in item
        for item in products
    ):
        return validate_plan(products)

    prompt = f"""
Converti cada producto en una busqueda de supermercado.

REQUIRED RULES:
- Responde SOLAMENTE JSON valido.
- No escribas explicaciones.
- No uses markdown.
- No uses ```json.
- No agregues texto antes ni despues.
- Mantené cantidad exacta.
- No cambies numeros.
- No agregues productos.
- No elimines productos.
- query siempre en español.
- query siempre en singular.

EXACT FORMAT:
[
    {{"query":"leche entera","quantity":2}}
]

PRODUCTS:
{json.dumps(products, ensure_ascii=False)}
"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Sos convertidor estricto de JSON. Responde solo JSON valido, sin texto extra. Responde siempre en español y usa query en singular."
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

    debug_print("\n🧠 Planner response:")
    debug_print(raw)

    data = extract_json(raw)
    return validate_plan(data)


def generate_shopping_list_from_prompt(user_prompt):
    prompt = f"""
Converti pedido de compra de usuario en lista JSON.

REQUIRED RULES:
- Responde SOLAMENTE JSON valido.
- No escribas explicaciones.
- No uses markdown.
- No agregues texto antes ni despues.
- Mantené cantidades como enteros.
- Si cantidad no es explicita, usa 1.
- Cada item debe tener query y quantity.
- query siempre en español.
- query siempre en singular.

EXACT FORMAT:
[
    {{"query":"leche","quantity":2}},
    {{"query":"shampoo","quantity":1}}
]

USER REQUEST:
{user_prompt}
"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Sos generador estricto de JSON para listas de compra. Responde solo JSON valido. Responde siempre en español y usa query en singular."
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

    debug_print("\n🧠 Shopping list generation response:")
    debug_print(raw)

    data = extract_json(raw)
    return validate_plan(data)