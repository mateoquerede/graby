"""
Add product module

Handles adding products to the cart on Coto Digital website.
"""

from shopping_copilot.src.evaluator import evaluate_product_with_ai
from shopping_copilot.src.config import BLOCKED, RULES, debug_print
from shopping_copilot.src.product_parser import extract_candidates


def handle_coto_modal(page):
    """Accept confirmation dialogs that block product addition (guest/login and address prompts)."""
    try:
        page.wait_for_timeout(300)
        selectors = [
            "dialog",
            "[role='dialog']",
            ".modal",
            ".modal-dialog",
            ".popup",
            ".overlay",
        ]

        for selector in selectors:
            modal = page.locator(selector).first
            if modal.count() == 0 or not modal.is_visible(timeout=400):
                continue

            text = (modal.inner_text(timeout=1000) or "").lower()
            if not any(keyword in text for keyword in [
                "aceptar",
                "cancelar",
                "ingresá",
                "iniciar sesión",
                "continuar como invitado",
                "dirección",
                "entregar",
                "enviar",
                "confirmar",
            ]):
                continue

            for button_selector in [
                "button:has-text('Aceptar')",
                "button:has-text('Confirmar')",
                "button:has-text('OK')",
                "[role='button']:has-text('Aceptar')",
                "[role='button']:has-text('Confirmar')",
            ]:
                button = page.locator(button_selector).first
                if button.count() > 0 and button.is_visible(timeout=500):
                    button.click(timeout=3000)
                    page.wait_for_timeout(1200)
                    return True

            return True
    except Exception as exc:
        debug_print(f"⚠️ No modal to handle or it was already dismissed: {exc}")

    return False


# Coto renders a *second*, hidden copy of a product card inside the floating
# cart preview (`cart-float` / `.dropdown-carrito`) as soon as anything is
# added to the cart. That clone carries the exact same
# `data-cnstrc-item-id` as the real, visible search-result card
# (`constructor-result-item`). A plain `querySelector`/`.first` lookup can
# therefore silently resolve to the wrong (hidden) node depending on DOM
# insertion order, so every helper below explicitly resolves the real,
# visible card first and only falls back to any match as a last resort.
_RESOLVE_REAL_CARD_JS = """
    const candidates = [...document.querySelectorAll(`[data-cnstrc-item-id="${itemId}"]`)];
    if (!candidates.length) return null;
    const real = candidates.find(el => !el.closest('cart-float, .dropdown-carrito, [id^="notificacion"]'));
    return real || candidates[0];
"""


def click_plus_by_item_id(page, item_id, target_quantity):
    target_quantity = float(target_quantity)
    if target_quantity <= 0:
        return

    stable_reads = 0

    for _ in range(120):
        state = page.evaluate(
            r"""
            (itemId) => {
                const resolveRealCard = (itemId) => {
                    %s
                };
                const card = resolveRealCard(itemId);
                if (!card) return { ok: false, reason: "card_not_found" };

                const selectors = [
                    '.input-spinner',
                    '.quantity-selector',
                    '[class*="spinner"]',
                    '[class*="qty"]',
                    '[class*="quantity"]'
                ];

                let spinner = null;
                for (const selector of selectors) {
                    spinner = card.querySelector(selector);
                    if (spinner) break;
                }
                if (!spinner) return { ok: false, reason: "spinner_not_found" };

                const input = spinner.querySelector('input');
                if (input) {
                    const value = Number(input.value || 0);
                    return { ok: true, value, has_input: true };
                }

                const numbers = (spinner.textContent || '').match(/-?\d+(?:[.,]\d+)?/g);
                if (numbers && numbers.length) {
                    const last = numbers[numbers.length - 1].replace(',', '.');
                    return { ok: true, value: Number(last), has_input: false };
                }

                const buttons = [...spinner.querySelectorAll('button')];
                const plus = buttons.find(btn => {
                    const text = (btn.textContent || '').trim();
                    const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                    const title = (btn.getAttribute('title') || '').toLowerCase();
                    return text === '+' || text.includes('+') || aria.includes('sumar') || title.includes('sumar') || aria.includes('increase') || title.includes('increase');
                });
                if (!plus) return { ok: false, reason: 'plus_not_found' };
                return { ok: true, value: 0, has_input: false, plus_present: true };
            }
            """
            % _RESOLVE_REAL_CARD_JS,
            item_id,
        )

        if not state.get("ok"):
            if state.get("reason") in {"card_not_found", "spinner_not_found", "plus_not_found"}:
                page.wait_for_timeout(150)
                continue
            raise Exception(f"Unable to read quantity state: {state}")

        value = state.get("value")
        if isinstance(value, (int, float)) and value >= target_quantity - 1e-6:
            # Require the target to hold steady across a short settle window
            # before trusting it: Coto's quantity update is not synchronous,
            # so a value can briefly "look" correct and then snap back.
            stable_reads += 1
            if stable_reads >= 2:
                return
            page.wait_for_timeout(400)
            continue

        stable_reads = 0

        clicked = page.evaluate(
            """
            (itemId) => {
                const resolveRealCard = (itemId) => {
                    %s
                };
                const card = resolveRealCard(itemId);
                if (!card) return false;

                const selectors = [
                    '.input-spinner',
                    '.quantity-selector',
                    '[class*="spinner"]',
                    '[class*="qty"]',
                    '[class*="quantity"]'
                ];

                let spinner = null;
                for (const selector of selectors) {
                    spinner = card.querySelector(selector);
                    if (spinner) break;
                }
                if (!spinner) return false;

                const buttons = [...spinner.querySelectorAll('button')];
                const plus = buttons.find(btn => {
                    const text = (btn.textContent || '').trim();
                    const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                    const title = (btn.getAttribute('title') || '').toLowerCase();
                    return text === '+' || text.includes('+') || aria.includes('sumar') || title.includes('sumar') || aria.includes('increase') || title.includes('increase');
                }) || buttons[buttons.length - 1];

                if (!plus || plus.disabled) return false;
                plus.click();
                return true;
            }
            """
            % _RESOLVE_REAL_CARD_JS,
            item_id,
        )

        if not clicked:
            page.wait_for_timeout(150)
            continue

        # Give Angular's change detection / debounced persistence time to
        # actually register the click before we read the value again.
        page.wait_for_timeout(400)

    raise Exception(f"Unable to reach quantity {target_quantity} for item {item_id}")


def add_by_plu(page, selected_plu, quantity):
    selected_plu = str(selected_plu)

    # Prefer the real, visible search-result card. Falls back to the plain
    # attribute selector if the results grid isn't wrapped the usual way
    # (e.g. a different page layout).
    scoped_locator = page.locator(
        f'constructor-result-item [data-cnstrc-item-id$="{selected_plu}"]'
    ).first
    card = scoped_locator if scoped_locator.count() > 0 else page.locator(
        f'[data-cnstrc-item-id$="{selected_plu}"]'
    ).first

    card.wait_for(state="attached", timeout=15000)

    item_id = card.get_attribute("data-cnstrc-item-id")

    debug_print(f"PLU selector: {selected_plu}")
    debug_print(f"Resolved item_id: {item_id}")

    # Handle address popup before clicking add button
    try:
        page.wait_for_timeout(500)
        popup_selectors = [
            ".modal",
            ".modal-dialog", 
            "[role='dialog']",
            ".modal-content",
            ".popup"
        ]
        
        for selector in popup_selectors:
            popup = page.locator(selector).first
            if popup.count() > 0 and popup.is_visible(timeout=500):
                popup_text = popup.inner_text(timeout=1000)
                if any(keyword in popup_text.lower() for keyword in ["dirección", "enviar", "entregar", "cambiar"]):
                    confirm_button = page.get_by_text("Confirmar", exact=False).first
                    if confirm_button.count() > 0 and confirm_button.is_visible(timeout=500):
                        confirm_button.click(timeout=3000)
                        debug_print("✅ Address popup handled in add_by_plu")
                        page.wait_for_timeout(1500)
                        break
    except Exception as e:
        debug_print(f"⚠️ No address popup in add_by_plu: {e}")

    btn = card.locator("button:has-text('Agregar')").first
    btn.wait_for(state="visible", timeout=15000)

    btn.click()
    handle_coto_modal(page)

    # Let the "just added" state (and its floating cart clone) settle before
    # we start reading/clicking the quantity spinner.
    page.wait_for_timeout(500)

    print(f"Producto agregado con PLU {selected_plu}")

    handle_coto_modal(page)
    click_plus_by_item_id(page, item_id, quantity)

    print(f"Agregado x{quantity}")


def add_product(page, quantity, requested_product=None):
    print(f"Agregando {quantity} unidades")

    # No forzamos ordenar por precio mínimo antes de evaluar: eso prioriza
    # variantes baratas y ambiguas sobre equivalencia semántica.
    candidates = extract_candidates(page, quantity)

    if not candidates:
        raise Exception("Unable to extract candidates")

    if len(candidates) == 1:
        selected_plu = candidates[0]["plu"]

        print(f"Un solo producto encontrado, seleccionando PLU {selected_plu}")

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
        f"Producto seleccionado: PLU {selected_plu}"
        f" | motivo: {decision.get('reason')}"
    )

    if not selected_plu:
        raise Exception("AI did not select a valid product")

    add_by_plu(page, selected_plu, quantity)