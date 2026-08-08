"""
Evaluator module

Uses AI to evaluate and select the best product match from search results
based on rules, blocked items, and pricing criteria.
"""

import json
import re
import ollama


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


def evaluate_product_with_ai(requested_product, quantity, candidates, blocked, rules):
    model_name = rules.get("ollama_model", "llama3")

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
        key=lambda c: c.get("effective_price_per_normalized_unit") or 999999999
    )

    for idx, c in enumerate(filtered_candidates):
        c["rank_by_normalized_price"] = idx + 1

    if not filtered_candidates:
        return {
            "selected_plu": None,
            "reason": "No valid candidates after hard filters"
        }

    prompt = f"""
Responde SOLO con JSON valido. Nada antes. Nada despues.

Producto pedido: {requested_product}
Cantidad requerida: {quantity}

PLUs bloqueados, NO los elijas:
{json.dumps(list(blocked_plu), ensure_ascii=False)}

Reglas:
{json.dumps(rules, ensure_ascii=False, indent=2)}

Candidatos permitidos, ya ordenados por precio normalizado:
{json.dumps(filtered_candidates, ensure_ascii=False, indent=2)}

Criterios obligatorios:
- selected_plu debe ser uno de los candidatos permitidos.
- Metrica principal de precio: effective_price_per_normalized_unit.
- NO uses price como criterio principal.
- price es solo precio de paquete y no compara tamanos distintos.
- Item 200ml gana SOLO si precio unitario normalizado es menor que opcion 1L.
- Si precio por litro de 200ml es mayor que opcion 1L, NO elegir.
- Considera promociones solo si aplican para cantidad requerida.
- Prioriza equivalencia semantica con producto pedido.
- Evita variantes no deseadas: chocolate, saborizado, sin lactosa, infantil.
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
                "content": "Responde solo JSON valido. No expliques. No uses markdown. reason siempre en español argentino."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0,
            "num_predict": 180
        }
    )

    raw = r["message"]["content"]

    print("\n🧠 AI evaluation:")
    print(raw)

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
        selected_ppu = selected_candidate.get("effective_price_per_normalized_unit")
        best_ppu = best_candidate.get("effective_price_per_normalized_unit")

        if selected_ppu and best_ppu:
            if selected_ppu > best_ppu * 1.10:
                return {
                    "selected_plu": str(best_candidate["plu"]),
                    "reason": (
                        f"Automatic override: AI selected PLU {selected}, "
                        f"but its normalized price {selected_ppu} is >10% worse "
                        f"than {best_candidate['plu']} with {best_ppu}"
                    )
                }

    return {
        "selected_plu": selected,
        "reason": decision.get("reason", "")
    }