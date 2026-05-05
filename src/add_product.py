"""
Add product module

Handles adding products to the cart on Coto Digital website.
"""

from evaluator import evaluar_producto_con_ia
from config import BLOQUEADOS, RULES
from search import ordenar_menor_precio
from product_parser import extraer_candidatos


def click_plus_por_item_id(page, item_id, veces):
    for n in range(veces):
        result = page.evaluate(
            """
            (itemId) => {
                const card = document.querySelector(`[data-cnstrc-item-id="${itemId}"]`);
                if (!card) return { ok:false, reason:"card_not_found" };

                const spinners = [...card.querySelectorAll(".input-spinner")];
                if (!spinners.length) return { ok:false, reason:"spinner_not_found" };

                const spinner =
                    spinners.find(s => getComputedStyle(s).display !== "none") ||
                    spinners[0];

                const buttons = spinner.querySelectorAll("button");
                if (buttons.length < 2) return { ok:false, reason:"plus_not_found" };

                buttons[1].click();

                const input = spinner.querySelector("input");

                return {
                    ok: true,
                    value: input ? input.value : null
                };
            }
            """,
            item_id,
        )

        print("➕ resultado:", result)

        if not result.get("ok"):
            raise Exception(f"No pude clickear +: {result}")

        page.wait_for_timeout(900)


def agregar_por_plu(page, selected_plu, cantidad):
    selected_plu = str(selected_plu)

    card = page.locator(
        f'[data-cnstrc-item-id$="{selected_plu}"]'
    ).first

    card.wait_for(state="attached", timeout=15000)

    item_id = card.get_attribute("data-cnstrc-item-id")

    print(f"Selector por PLU: {selected_plu}")
    print(f"item_id real: {item_id}")

    btn = card.locator("button:has-text('Agregar')").first
    btn.wait_for(state="visible", timeout=15000)

    btn.click()

    print(f"✅ Producto agregado PLU {selected_plu}")

    page.wait_for_timeout(3000)

    if cantidad <= 1:
        return

    click_plus_por_item_id(page, item_id, cantidad - 1)

    print(f"✅ agregado x{cantidad}")


def agregar_producto(page, cantidad, producto_pedido=None):
    print(f"🛒 Agregando {cantidad} unidades")

    candidatos = extraer_candidatos(page, cantidad)

    if not candidatos:
        raise Exception("No se pudieron extraer candidatos")

    if len(candidatos) == 1:
        selected_plu = candidatos[0]["plu"]

        print(f"✅ Único producto encontrado, se elige directo PLU {selected_plu}")

        agregar_por_plu(page, selected_plu, cantidad)

        return

    ordenar_menor_precio(page)

    candidatos = extraer_candidatos(page, cantidad)

    if not candidatos:
        raise Exception("No se pudieron extraer candidatos después de ordenar")

    decision = evaluar_producto_con_ia(
        producto_pedido=producto_pedido or "producto solicitado",
        cantidad=cantidad,
        candidatos=candidatos,
        bloqueados=BLOQUEADOS,
        rules=RULES
    )

    selected_plu = decision.get("selected_plu")

    print("🧠 PLU elegido:", selected_plu)
    print("🧠 Motivo:", decision.get("reason"))

    if not selected_plu:
        raise Exception("La IA no eligió ningún producto válido")

    agregar_por_plu(page, selected_plu, cantidad)