"""
Product parser module.

Contains functions for parsing product information, prices, units, and promotions
from Coto Digital website.
"""

import json
import re

def get_card_from_button(btn):
    for level in range(1, 12):
        try:
            container = btn.locator(f"xpath=ancestor::*[{level}]")
            item_id = container.get_attribute("data-cnstrc-item-id", timeout=1000)

            if item_id:
                match = re.search(r"prod0*([0-9]+)", item_id)
                if match:
                    return container, match.group(1), item_id
        except Exception:
            pass

    return None, None, None


def get_add_buttons(page):
    selectors = [
        "button:has-text('Agregar')",
        "a:has-text('Agregar')",
        "[role='button']:has-text('Agregar')",
        ".btn:has-text('Agregar')",
    ]

    for selector in selectors:
        loc = page.locator(selector)
        count = loc.count()
        print(f"Selector {selector} -> {count}")

        if count > 0:
            return loc

    return None


def parse_argentinian_price(s):
    if not s:
        return None

    s = str(s).replace("$", "").strip()

    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        parts = s.split(".")
        if len(parts) > 2:
            s = s.replace(".", "")
        elif len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(".", "")

    try:
        return float(s)
    except Exception:
        return None


def parse_float_price(value):
    return parse_argentinian_price(value)


def parse_coto_normalized_price(text):
    patterns = [
        r"Precio por\s+1\s+Litro:\s*\$ ?([\d\.\,]+)",
        r"Precio por\s+1\s+L:\s*\$ ?([\d\.\,]+)",
        r"Precio por\s+1\s+Kg:\s*\$ ?([\d\.\,]+)",
        r"Precio por\s+1\s+Kilo:\s*\$ ?([\d\.\,]+)",
        r"Precio por\s+Unidad:\s*\$ ?([\d\.\,]+)",
        r"Precio por\s+1\s+Unidad:\s*\$ ?([\d\.\,]+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return parse_argentinian_price(m.group(1))

    return None


def parse_unit(name, text):
    raw = f"{name} {text}".lower()

    m = re.search(r"(\d+(?:[\.,]\d+)?)\s*(l|lt|litro|litros)\b", raw)
    if m:
        return {
            "amount": float(m.group(1).replace(",", ".")),
            "unit": "l"
        }

    m = re.search(r"(\d+(?:[\.,]\d+)?)\s*(ml|cc)\b", raw)
    if m:
        return {
            "amount": float(m.group(1).replace(",", ".")) / 1000,
            "unit": "l"
        }

    m = re.search(r"(\d+(?:[\.,]\d+)?)\s*(kg|kilo|kilos)\b", raw)
    if m:
        return {
            "amount": float(m.group(1).replace(",", ".")),
            "unit": "kg"
        }

    m = re.search(r"(\d+(?:[\.,]\d+)?)\s*(g|gr|gramos)\b", raw)
    if m:
        return {
            "amount": float(m.group(1).replace(",", ".")) / 1000,
            "unit": "kg"
        }

    return {
        "amount": 1,
        "unit": "un"
    }


def extract_promos(text):
    promos = []
    t = text.upper()

    possible_promos = [
        "50% 2DA",
        "70% 2DA",
        "80% 2DA",
        "LLEVANDO 2",
        "LLEVANDO 3",
        "2X1",
        "3X2"
    ]

    for promo in possible_promos:
        if promo in t:
            promos.append(promo)

    return promos


def calculate_effective_price(unit_price, quantity, promos):
    if unit_price is None:
        return None

    total = unit_price * quantity
    promo_text = " ".join(promos).upper()

    if "2X1" in promo_text:
        paid = (quantity + 1) // 2
        return paid * unit_price

    if "3X2" in promo_text:
        groups = quantity // 3
        remainder = quantity % 3
        return (groups * 2 + remainder) * unit_price

    if "50% 2DA" in promo_text:
        pairs = quantity // 2
        remainder = quantity % 2
        return pairs * (unit_price * 1.5) + remainder * unit_price

    if "70% 2DA" in promo_text:
        pairs = quantity // 2
        remainder = quantity % 2
        return pairs * (unit_price * 1.3) + remainder * unit_price

    if "80% 2DA" in promo_text:
        pairs = quantity // 2
        remainder = quantity % 2
        return pairs * (unit_price * 1.2) + remainder * unit_price

    return total


def extract_candidates(page, quantity):
    products = get_add_buttons(page)

    if products is None:
        page.screenshot(path="debug_no_add_buttons.png", full_page=True)
        raise Exception("Could not find Add buttons")

    total = products.count()
    print("📦 Products found:", total)

    candidates = []

    for i in range(total):
        btn = products.nth(i)

        try:
            card, plu, item_id = get_card_from_button(btn)

            if not card or not plu:
                print("⚠️ Product without detectable PLU")
                continue

            text = card.inner_text(timeout=2000)

            item_name = card.get_attribute("data-cnstrc-item-name") or ""
            item_price = parse_float_price(
                card.get_attribute("data-cnstrc-item-price")
            )

            unit = parse_unit(item_name, text)
            promos = extract_promos(text)

            coto_normalized_price = parse_coto_normalized_price(text)

            effective_total_price = calculate_effective_price(
                item_price,
                quantity,
                promos
            )

            if coto_normalized_price is not None:
                effective_normalized_unit_price = coto_normalized_price
            elif effective_total_price is not None and unit["amount"] > 0:
                effective_normalized_unit_price = (
                    effective_total_price / quantity / unit["amount"]
                )
            else:
                effective_normalized_unit_price = None

            candidate = {
                "index": i,
                "plu": plu,
                "item_id": item_id,
                "name": item_name,
                "price": item_price,
                "unit_amount": unit["amount"],
                "unit": unit["unit"],
                "promos": promos,
                "coto_normalized_price": coto_normalized_price,
                "effective_total_price": effective_total_price,
                "effective_price_per_normalized_unit": effective_normalized_unit_price,
                "raw_text": text[:1200]
            }

            print("\n------")
            print(json.dumps(candidate, ensure_ascii=False, indent=2))

            candidates.append(candidate)

        except Exception as e:
            print("⚠️ Error reading candidate:", e)

    return candidates
