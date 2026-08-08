"""
Add product module

Handles adding products to the cart on Coto Digital website.
"""

from shopping_copilot.src.evaluator import evaluate_product_with_ai
from shopping_copilot.src.config import BLOCKED, RULES, debug_print
from shopping_copilot.src.search import sort_by_lowest_price
from shopping_copilot.src.product_parser import extract_candidates


def click_plus_by_item_id(page, item_id, times):
    for _ in range(times):
        retries = 0
        while True:
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

                    const input = spinner.querySelector("input");
                    const before = input ? Number(input.value) : null;

                    buttons[1].click();

                    const after = input ? input.value : null;

                    return {
                        ok: true,
                        before,
                        after
                    };
                }
                """,
                item_id,
            )

            if result.get("ok"):
                break

            if result.get("reason") in {"card_not_found", "spinner_not_found", "plus_not_found"} and retries < 12:
                retries += 1
                page.wait_for_timeout(150)
                continue

            raise Exception(f"Unable to click +: {result}")

        debug_print("➕ result:", result)

        before = result.get("before")
        if isinstance(before, (int, float)):
            expected = int(before) + 1
            page.wait_for_function(
                """
                ([itemId, expectedValue]) => {
                    const card = document.querySelector(`[data-cnstrc-item-id="${itemId}"]`);
                    if (!card) return false;
                    const spinner =
                        [...card.querySelectorAll('.input-spinner')].find(s => getComputedStyle(s).display !== 'none') ||
                        card.querySelector('.input-spinner');
                    if (!spinner) return false;
                    const input = spinner.querySelector('input');
                    return input && Number(input.value) === expectedValue;
                }
                """,
                arg=[item_id, expected],
                timeout=3000,
            )
        else:
            page.wait_for_timeout(250)


def add_by_plu(page, selected_plu, quantity):
    selected_plu = str(selected_plu)

    card = page.locator(
        f'[data-cnstrc-item-id$="{selected_plu}"]'
    ).first

    card.wait_for(state="attached", timeout=15000)

    item_id = card.get_attribute("data-cnstrc-item-id")

    debug_print(f"PLU selector: {selected_plu}")
    debug_print(f"Resolved item_id: {item_id}")

    btn = card.locator("button:has-text('Agregar')").first
    btn.wait_for(state="visible", timeout=15000)

    btn.click()

    print(f"✅ Added product PLU {selected_plu}")

    if quantity <= 1:
        return

    click_plus_by_item_id(page, item_id, quantity - 1)

    print(f"✅ added x{quantity}")


def add_product(page, quantity, requested_product=None):
    print(f"🛒 Adding {quantity} units")

    sort_by_lowest_price(page)

    candidates = extract_candidates(page, quantity)

    if not candidates:
        raise Exception("Unable to extract candidates")

    if len(candidates) == 1:
        selected_plu = candidates[0]["plu"]

        print(f"✅ Single product found, selecting PLU {selected_plu}")

        add_by_plu(page, selected_plu, quantity)

        return

    if not candidates:
        raise Exception("Unable to extract candidates after sorting")

    decision = evaluate_product_with_ai(
        requested_product=requested_product or "requested product",
        quantity=quantity,
        candidates=candidates,
        blocked=BLOCKED,
        rules=RULES
    )

    selected_plu = decision.get("selected_plu")

    print(
        f"🧠 Selected product: PLU {selected_plu}"
        f" | reason: {decision.get('reason')}"
    )

    if not selected_plu:
        raise Exception("AI did not select a valid product")

    add_by_plu(page, selected_plu, quantity)