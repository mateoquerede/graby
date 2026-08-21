"""
Planner module

Uses an LLM to convert product names into optimized search queries
for supermarket shopping, maintaining exact quantities.
"""

import json
import re
from shopping_copilot.src.config import debug_print, LLM_MAX_TOKENS
from shopping_copilot.src.ai_guard import validate_ai_input, validate_item_limits
from shopping_copilot.src.llm_service import LLMService


NUMBER_WORDS = {
    "cero": 0,
    "uno": 1,
    "una": 1,
    "un": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "veinte": 20,
}

SHOPPING_EXTRACTION_RULES = """
Reglas de extracción obligatorias:
- Cada elemento del JSON debe ser un producto real y completo.
- La cantidad se toma del número que aparece junto al producto; si no hay número, la cantidad es 1.
- No cambies la cantidad ni la conviertas en texto.
- El query debe quedar en español y en singular.
- No dividas marcas ni tipos de producto en dos items distintos.
- 'fernet branca' es un único producto, no 'fernet' + 'branca'.
- '1 pan' es [{"query":"pan","quantity":1}], no dos productos ni cantidad distinta.
- '1 supremas' es [{"query":"suprema","quantity":1}].
- '2 huevos' es [{"query":"huevo","quantity":2}].
- Si hay varios productos, separalos solo por comas, punto y coma o por productos distintos reales.
- No inventes marcas, sabores, tamaños ni elementos que no estén en el pedido.
- No uses markdown, ni texto fuera del JSON.
"""


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
    Works even if the model adds text before or after.
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


def _extract_quantity_from_text(text):
    text = str(text or "").strip()
    if not text:
        return 1

    match = re.search(r"\b(\d+(?:[.,]\d+)?)", text)
    if match:
        value = float(match.group(1).replace(",", "."))
        return max(1, value)

    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", text, flags=re.IGNORECASE):
            return max(1, value)

    return 1


def _clean_product_phrase(text):
    text = str(text or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^(?:un|una|uno|de|del|la|las|el|los|y|e)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:caja|cajas|paquete|paquetes|botella|botellas|pack)\s+de\s+", "", text, flags=re.IGNORECASE)
    text = text.strip(" ,;.-_")
    return text


def parse_user_prompt_to_items(user_prompt):
    text = str(user_prompt or "").strip()
    if not text:
        return []

    parts = re.split(r"\s*(?:,|;|\n|\s\by\b|\s\be\b)+\s*", text, flags=re.IGNORECASE)
    items = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        quantity = _extract_quantity_from_text(part)
        phrase = _clean_product_phrase(part)
        phrase = re.sub(
            rf"^(?:{ '|'.join(re.escape(v) for v in NUMBER_WORDS) }|\d+(?:[.,]\d+)?"
            rf"\s*(?:kg|kgs|kilo(?:s)?|g|gr|gramo(?:s)?|l|lt|lts|litro(?:s)?|"
            rf"ml|unidad(?:es)?|pack|caja(?:s)?|botella(?:s)?)?)\s*",
            "",
            phrase,
            flags=re.IGNORECASE,
        )
        phrase = _clean_product_phrase(phrase)
        phrase = re.sub(
            r"\s+\d+(?:[.,]\d+)?\s*(?:kg|kgs|kilo(?:s)?|g|gr|gramo(?:s)?|"
            r"l|lt|lts|litro(?:s)?|ml)\b$",
            "",
            phrase,
            flags=re.IGNORECASE,
        ).strip()
        phrase = singularize_spanish_query(phrase)

        if not phrase:
            continue

        items.append({
            "query": phrase,
            "quantity": quantity,
        })

    return items


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
        normalized_query = re.sub(r"\s+", " ", normalized_query).strip()
        if not normalized_query:
            raise ValueError(f"Invalid query in item: {item}")

        normalized_quantity = float(quantity)
        if normalized_quantity < 1:
            raise ValueError(f"Quantity must be >= 1 in item: {item}")

        if normalized_quantity.is_integer():
            normalized_quantity = int(normalized_quantity)

        validated.append({
            "query": normalized_query,
            "quantity": normalized_quantity
        })

    return validate_item_limits(validated)


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

{SHOPPING_EXTRACTION_RULES}

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
- No separes una marca con su tipo de producto. 'fernet branca' es una sola query.

EXACT FORMAT:
[
    {{"query":"leche entera","quantity":2}}
]

PRODUCTS:
{json.dumps(products, ensure_ascii=False)}
"""

    raw = LLMService().complete_json(
        messages=[
            {
                "role": "system",
                "content": "Sos un convertidor estricto de JSON para compras. Responde solo JSON valido. Sigue estas reglas: " + SHOPPING_EXTRACTION_RULES + " No expliques, no agregues texto. Usa query en español y singular. Nunca dividas una marca y un tipo de producto en dos items."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=LLM_MAX_TOKENS,
        temperature=0,
        top_p=0.1,
    )

    debug_print("\n🧠 Planner response:")
    debug_print(raw)

    data = extract_json(raw)
    return validate_plan(data)


def generate_shopping_list_from_prompt(user_prompt):
    text = validate_ai_input(user_prompt)
    parsed = parse_user_prompt_to_items(text)
    if parsed:
        return validate_plan(parsed)

    prompt = f"""
    Converti pedido de compra de usuario en lista JSON.

    {SHOPPING_EXTRACTION_RULES}

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
    - No dividas marcas ni tipos de producto en dos items distintos.
    - "fernet branca" debe mantenerse como una sola query.
    - "1 pan" no se vuelve "pan" y "1" ni "panes".

    EXACT FORMAT:
    [
        {{"query":"leche","quantity":2}},
        {{"query":"shampoo","quantity":1}}
    ]

    USER REQUEST:
    {user_prompt}
    """

    raw = LLMService().complete_json(
        messages=[
            {
                "role": "system",
                "content": "Sos generador estricto de JSON para listas de compra. Responde solo JSON valido. Sigue estas reglas: " + SHOPPING_EXTRACTION_RULES + " Respeta cantidades exactas y nunca dividas marca + producto en dos items."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=LLM_MAX_TOKENS,
        temperature=0,
        top_p=0.1,
    )

    debug_print("\n🧠 Shopping list generation response:")
    debug_print(raw)

    data = extract_json(raw)
    return validate_plan(data)