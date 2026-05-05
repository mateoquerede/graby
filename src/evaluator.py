"""
Evaluator module

Uses AI to evaluate and select the best product match from search results
based on rules, blocked items, and pricing criteria.
"""

import json
import re
import ollama


def extraer_json_objeto(raw):
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
        "reason": "La IA no devolvió JSON válido con selected_plu"
    }


def evaluar_producto_con_ia(producto_pedido, cantidad, candidatos, bloqueados, rules):
    modelo = rules.get("modelo_ollama", "llama3")

    bloqueados_plu = set(str(x) for x in bloqueados.get("plu", []))

    candidatos_filtrados = [
        c for c in candidatos
        if str(c.get("plu")) not in bloqueados_plu
    ]

    candidatos_filtrados = [
        c for c in candidatos_filtrados
        if c.get("effective_price_per_normalized_unit") is not None
    ]

    candidatos_filtrados = sorted(
        candidatos_filtrados,
        key=lambda c: c.get("effective_price_per_normalized_unit") or 999999999
    )

    for idx, c in enumerate(candidatos_filtrados):
        c["rank_by_normalized_price"] = idx + 1

    if not candidatos_filtrados:
        return {
            "selected_plu": None,
            "reason": "No hay candidatos válidos después de filtros duros"
        }

    prompt = f"""
Respondé SOLO un JSON válido. Nada antes. Nada después.

Producto pedido: {producto_pedido}
Cantidad requerida: {cantidad}

PLU bloqueados, NO PODÉS elegirlos:
{json.dumps(list(bloqueados_plu), ensure_ascii=False)}

Reglas:
{json.dumps(rules, ensure_ascii=False, indent=2)}

Candidatos permitidos, ya ordenados por precio normalizado:
{json.dumps(candidatos_filtrados, ensure_ascii=False, indent=2)}

Criterios obligatorios:
- selected_plu debe ser uno de los candidatos permitidos.
- El criterio principal de precio es effective_price_per_normalized_unit.
- NO usar price como criterio principal.
- price es solo el precio del envase, no sirve para comparar tamaños distintos.
- Un producto de 200ml puede ganar SOLO si effective_price_per_normalized_unit es menor que las opciones de 1L.
- Si el producto de 200ml tiene mayor precio por litro que uno de 1L, NO elegirlo.
- Considerar promociones solo si aplican a la cantidad requerida.
- Priorizar equivalencia semántica con el producto pedido.
- Evitar variantes no pedidas: chocolatada, saborizada, sin lactosa, deslactosada, infantil.
- Si ningún candidato sirve, selected_plu debe ser null.

Formato exacto:
{{
  "selected_plu": "string|null",
  "reason": "string corto"
}}
"""

    r = ollama.chat(
        model=modelo,
        messages=[
            {
                "role": "system",
                "content": "Respondé únicamente JSON válido. No expliques. No uses markdown."
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

    print("\n🧠 Evaluación IA:")
    print(raw)

    decision = extraer_json_objeto(raw)

    selected = decision.get("selected_plu")

    if selected is not None:
        selected = str(selected)

    validos = set(str(c["plu"]) for c in candidatos_filtrados)

    if selected not in validos:
        return {
            "selected_plu": None,
            "reason": f"La IA eligió un PLU inválido o bloqueado: {selected}"
        }

    selected_candidate = next(
        (c for c in candidatos_filtrados if str(c["plu"]) == selected),
        None
    )

    best_candidate = candidatos_filtrados[0]

    if selected_candidate and best_candidate:
        selected_ppu = selected_candidate.get("effective_price_per_normalized_unit")
        best_ppu = best_candidate.get("effective_price_per_normalized_unit")

        if selected_ppu and best_ppu:
            if selected_ppu > best_ppu * 1.10:
                return {
                    "selected_plu": str(best_candidate["plu"]),
                    "reason": (
                        f"Override automático: la IA eligió PLU {selected}, "
                        f"pero su precio normalizado {selected_ppu} es >10% peor "
                        f"que {best_candidate['plu']} con {best_ppu}"
                    )
                }

    return {
        "selected_plu": selected,
        "reason": decision.get("reason", "")
    }