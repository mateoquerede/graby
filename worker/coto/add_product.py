"""Product selection and cart operations using Coto's HTTP APIs."""

import json

from shopping_copilot.src.config import BLOCKED, RULES
from shopping_copilot.src.config import debug_print
from shopping_copilot.src.evaluator import evaluate_product_with_ai
from shopping_copilot.src.product_parser import extract_api_candidates


def add_product_with_result(client, payload, quantity: int, requested_product: str = ""):
    debug_print(
        "Coto product search response:",
        json.dumps(payload, ensure_ascii=False)[:12000],
    )
    candidates = extract_api_candidates(payload, quantity)
    debug_print(f"Coto normalized candidates: {len(candidates)}")
    if not candidates:
        return None

    if len(candidates) == 1:
        selected = candidates[0]
        reason = "Único resultado disponible."
    else:
        decision = evaluate_product_with_ai(
            requested_product=requested_product or "producto",
            quantity=quantity,
            candidates=candidates,
            blocked=BLOCKED,
            rules=RULES,
        )
        selected_plu = str(decision.get("selected_plu") or "")
        selected = next(
            (candidate for candidate in candidates if candidate["plu"] == selected_plu),
            None,
        )
        if not selected:
            return None
        reason = decision.get("reason", "")

    client.add_item(selected["product_id"], selected["sku_id"], quantity)
    return {
        "requested": requested_product,
        "name": selected["name"] or selected["plu"],
        "plu": selected["plu"],
        "quantity": quantity,
        "price": selected["price"],
        "reason": reason,
    }
