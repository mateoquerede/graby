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

        validated.append({
            "query": str(query).strip(),
            "quantity": int(float(quantity))
        })

    return validated


def plan(products):
    prompt = f"""
Convert each product into a supermarket search.

REQUIRED RULES:
- Return ONLY valid JSON.
- Do not write explanations.
- Do not use markdown.
- Do not use ```json.
- Do not add text before or after.
- Keep the exact quantity.
- Do not change numbers.
- Do not add products.
- Do not remove products.

EXACT FORMAT:
[
  {{"query":"whole milk","quantity":2}}
]

PRODUCTS:
{json.dumps(products, ensure_ascii=False)}
"""

    response = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "system",
                "content": "You are a strict JSON converter. Respond only with valid JSON, without additional text."
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

    print("\n🧠 Planner response:")
    print(raw)

    data = extract_json(raw)
    return validate_plan(data)