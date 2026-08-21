"""
add_product variant that returns a structured result dict
instead of only printing to stdout.
"""

from shopping_copilot.src.evaluator import evaluate_product_with_ai
from shopping_copilot.src.config import BLOCKED, RULES
from shopping_copilot.src.product_parser import extract_candidates
from shopping_copilot.src.add_product import add_by_plu


def add_product_with_result(page, quantity: int, requested_product: str = "") -> dict | None:
    """
    Search results are already loaded. Sort, evaluate, add to cart,
    and return a result dict suitable for the API response.
    Returns None if no suitable product was found.
    """
    # Mantener el orden natural de resultados del buscador para priorizar
    # coincidencia semántica antes que el producto más barato.
    candidates = extract_candidates(page, quantity)

    if not candidates:
        return None

    if len(candidates) == 1:
        c = candidates[0]
        add_by_plu(page, c["plu"], quantity)
        return {
            "requested": requested_product,
            "name": c.get("name", c["plu"]),
            "plu": c["plu"],
            "quantity": quantity,
            "price": c.get("price"),
            "reason": "Único resultado disponible.",
        }

    decision = evaluate_product_with_ai(
        requested_product=requested_product or "producto",
        quantity=quantity,
        candidates=candidates,
        blocked=BLOCKED,
        rules=RULES,
    )

    selected_plu = decision.get("selected_plu")
    if not selected_plu:
        return None

    selected = next((c for c in candidates if str(c["plu"]) == str(selected_plu)), None)
    if not selected:
        return None

    add_by_plu(page, selected_plu, quantity)

    return {
        "requested": requested_product,
        "name": selected.get("name", selected_plu),
        "plu": selected_plu,
        "quantity": quantity,
        "price": selected.get("price"),
        "reason": decision.get("reason", ""),
    }
