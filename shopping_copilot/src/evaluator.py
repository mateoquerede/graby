"""
Evaluator module

Uses AI to evaluate and select the best product match from search results
based on rules, blocked items, and pricing criteria.
"""

import json
import re
import ollama
from shopping_copilot.src.config import debug_print, OLLAMA_MODEL, OLLAMA_NUM_PREDICT
from shopping_copilot.src.ai_guard import limit_candidates, validate_ai_input


def _normalize_for_match(value):
    text = str(value or "").lower()
    text = text.replace("&", " y ")
    text = re.sub(r"[^a-z0-9áéíóúüñ\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _semantic_match_score(requested_product, candidate_name):
    requested = _normalize_for_match(requested_product)
    candidate = _normalize_for_match(candidate_name)

    if not requested or not candidate:
        return 0

    if requested == candidate:
        return 100

    if requested in candidate or candidate in requested:
        return 90

    req_tokens = set(t for t in requested.split() if len(t) > 2)
    cand_tokens = set(t for t in candidate.split() if len(t) > 2)

    if not req_tokens or not cand_tokens:
        return 0

    overlap = len(req_tokens & cand_tokens)
    if overlap == 0:
        return 0

    return int((overlap / max(len(req_tokens | cand_tokens), 1)) * 100)


def extract_json_object(raw):
    matches = re.finditer(r"\{.*?\}", raw, re.DOTALL)

    for m in matches:
        txt = m.group(0)
        try:
            obj = json.loads(txt)
            if "selected_plu" in obj:
                return obj
        except Exception:
            pass

    return {
        "selected_plu": None,
        "reason": "AI did not return valid JSON with selected_plu"
    }


EVALUATOR_RULES = """
Reglas de selección de producto:
- El producto seleccionado debe coincidir con el nombre solicitado y no con una variante desalineada.
- La coincidencia semántica vale más que el precio más bajo.
- El precio normalizado sirve solo como desempate entre opciones equivalentes.
- Nunca dividas una marca y un tipo de producto en dos artículos distintos.
- 'fernet branca' debe tratarse como un solo producto. No elijas por separado 'fernet' y 'branca'.
- No elijas variantes no deseadas: chocolate, saborizado, sin lactosa, infantil, etc., salvo que el pedido las pida explícitamente.
- Si el producto pedido es genérico, prioriza la variante más cercana y útil, no la más barata o la más rara.
- Considera promociones solo si aplican a la cantidad requerida.
- Si no hay un candidato válido, responde null.
"""


def evaluate_product_with_ai(requested_product, quantity, candidates, blocked, rules):
    requested_product = validate_ai_input(
        requested_product, max_chars=120, require_shopping_terms=False
    )
    model_name = rules.get("ollama_model", OLLAMA_MODEL)

    blocked_plu = set(str(x) for x in blocked.get("plu", []))

    filtered_candidates = [
        c for c in candidates
        if str(c.get("plu")) not in blocked_plu
    ]

    filtered_candidates = [
        c for c in filtered_candidates
        if c.get("effective_price_per_normalized_unit") is not None
    ]

    filtered_candidates = sorted(
        filtered_candidates,
        key=lambda c: (
            -_semantic_match_score(requested_product, c.get("name") or ""),
            c.get("effective_price_per_normalized_unit") or 999999999,
        ),
    )
    filtered_candidates = limit_candidates(filtered_candidates)

    for idx, c in enumerate(filtered_candidates):
        c["rank_by_semantic_match"] = idx + 1

    if not filtered_candidates:
        return {
            "selected_plu": None,
            "reason": "No valid candidates after hard filters"
        }

    prompt = f"""
Responde SOLO con JSON valido. Nada antes. Nada despues.

{EVALUATOR_RULES}

Producto pedido: {requested_product}
Cantidad requerida: {quantity}

PLUs bloqueados, NO los elijas:
{json.dumps(list(blocked_plu), ensure_ascii=False)}

Reglas:
{json.dumps(rules, ensure_ascii=False, indent=2)}

Candidatos permitidos, ya ordenados por coincidencia semantica y luego precio:
{json.dumps(filtered_candidates, ensure_ascii=False, indent=2)}

Criterios obligatorios:
- selected_plu debe ser uno de los candidatos permitidos.
- Prioriza coincidencia semantica con el producto pedido sobre precio.
- price es solo precio de paquete y no compara tamaños distintos.
- effective_price_per_normalized_unit solo sirve como desempate entre opciones equivalentes.
- Item 200ml gana SOLO si precio unitario normalizado es menor que opcion 1L.
- Si precio por litro de 200ml es mayor que opcion 1L, NO elegir.
- Considera promociones solo si aplican para cantidad requerida.
- Evita variantes no deseadas: chocolate, saborizado, sin lactosa, infantil.
- No dividas una marca y un tipo de producto en dos items distintos.
- "fernet branca" debe mantenerse como una sola query/producto.
- Si no hay candidato valido, selected_plu debe ser null.
- reason debe estar en español argentino.

Exact format:
{{
  "selected_plu": "string|null",
    "reason": "texto corto en español argentino"
}}
"""

    r = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "Responde solo JSON valido. No expliques. No uses markdown. reason siempre en español argentino. " + EVALUATOR_RULES
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0,
            "num_predict": min(OLLAMA_NUM_PREDICT, 180)
        }
    )

    raw = r["message"]["content"]

    debug_print("\n🧠 AI evaluation:")
    debug_print(raw)

    decision = extract_json_object(raw)

    selected = decision.get("selected_plu")

    if selected is not None:
        selected = str(selected)

    valid_values = set(str(c["plu"]) for c in filtered_candidates)

    if selected not in valid_values:
        return {
            "selected_plu": None,
            "reason": f"AI selected an invalid or blocked PLU: {selected}"
        }

    selected_candidate = next(
        (c for c in filtered_candidates if str(c["plu"]) == selected),
        None
    )

    best_candidate = filtered_candidates[0]

    if selected_candidate and best_candidate:
        selected_score = _semantic_match_score(requested_product, selected_candidate.get("name") or "")
        best_score = _semantic_match_score(requested_product, best_candidate.get("name") or "")
        selected_ppu = selected_candidate.get("effective_price_per_normalized_unit")
        best_ppu = best_candidate.get("effective_price_per_normalized_unit")

        if selected_score < best_score and selected_ppu and best_ppu:
            return {
                "selected_plu": str(best_candidate["plu"]),
                "reason": (
                    f"Override automático: {best_candidate['plu']} coincide mejor con "
                    f"{requested_product} que {selected} y tiene mejor ajuste semántico."
                )
            }

        if selected_ppu and best_ppu:
            if selected_ppu > best_ppu * 1.10 and selected_score == best_score:
                return {
                    "selected_plu": str(best_candidate["plu"]),
                    "reason": (
                        f"Override automático: AI seleccionó PLU {selected}, "
                        f"pero el precio normalizado es >10% peor que {best_candidate['plu']}"
                    )
                }

    return {
        "selected_plu": selected,
        "reason": decision.get("reason", "")
    }