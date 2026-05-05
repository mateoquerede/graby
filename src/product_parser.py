"""
Product parser module.

Contains functions for parsing product information, prices, units, and promotions
from Coto Digital website.
"""

import json
import re


def obtener_card_desde_boton(btn):
    for nivel in range(1, 12):
        try:
            contenedor = btn.locator(f"xpath=ancestor::*[{nivel}]")
            item_id = contenedor.get_attribute("data-cnstrc-item-id", timeout=1000)

            if item_id:
                match = re.search(r"prod0*([0-9]+)", item_id)
                if match:
                    return contenedor, match.group(1), item_id

        except Exception:
            pass

    return None, None, None


def obtener_botones_agregar(page):
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


def parse_precio_argentino(s):
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
    return parse_precio_argentino(value)


def parse_precio_normalizado_coto(texto):
    patterns = [
        r"Precio por\s+1\s+Litro:\s*\$ ?([\d\.\,]+)",
        r"Precio por\s+1\s+L:\s*\$ ?([\d\.\,]+)",
        r"Precio por\s+1\s+Kg:\s*\$ ?([\d\.\,]+)",
        r"Precio por\s+1\s+Kilo:\s*\$ ?([\d\.\,]+)",
        r"Precio por\s+Unidad:\s*\$ ?([\d\.\,]+)",
        r"Precio por\s+1\s+Unidad:\s*\$ ?([\d\.\,]+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, texto, re.IGNORECASE)
        if m:
            return parse_precio_argentino(m.group(1))

    return None


def parse_unidad(nombre, texto):
    raw = f"{nombre} {texto}".lower()

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


def extraer_promos(texto):
    promos = []
    t = texto.upper()

    posibles = [
        "50% 2DA",
        "70% 2DA",
        "80% 2DA",
        "LLEVANDO 2",
        "LLEVANDO 3",
        "2X1",
        "3X2"
    ]

    for p in posibles:
        if p in t:
            promos.append(p)

    return promos


def calcular_precio_efectivo(precio_unitario, cantidad, promos):
    if precio_unitario is None:
        return None

    total = precio_unitario * cantidad
    promo_text = " ".join(promos).upper()

    if "2X1" in promo_text:
        pagas = (cantidad + 1) // 2
        return pagas * precio_unitario

    if "3X2" in promo_text:
        grupos = cantidad // 3
        resto = cantidad % 3
        return (grupos * 2 + resto) * precio_unitario

    if "50% 2DA" in promo_text:
        pares = cantidad // 2
        resto = cantidad % 2
        return pares * (precio_unitario * 1.5) + resto * precio_unitario

    if "70% 2DA" in promo_text:
        pares = cantidad // 2
        resto = cantidad % 2
        return pares * (precio_unitario * 1.3) + resto * precio_unitario

    if "80% 2DA" in promo_text:
        pares = cantidad // 2
        resto = cantidad % 2
        return pares * (precio_unitario * 1.2) + resto * precio_unitario

    return total


def extraer_candidatos(page, cantidad):
    productos = obtener_botones_agregar(page)

    if productos is None:
        page.screenshot(path="debug_sin_agregar.png", full_page=True)
        raise Exception("No encontré botones Agregar")

    total = productos.count()
    print("📦 Productos encontrados:", total)

    candidatos = []

    for i in range(total):
        btn = productos.nth(i)

        try:
            card, plu, item_id = obtener_card_desde_boton(btn)

            if not card or not plu:
                print("⚠️ Producto sin PLU detectable")
                continue

            texto = card.inner_text(timeout=2000)

            item_name = card.get_attribute("data-cnstrc-item-name") or ""
            item_price = parse_float_price(
                card.get_attribute("data-cnstrc-item-price")
            )

            unidad = parse_unidad(item_name, texto)
            promos = extraer_promos(texto)

            precio_normalizado_coto = parse_precio_normalizado_coto(texto)

            precio_efectivo_total = calcular_precio_efectivo(
                item_price,
                cantidad,
                promos
            )

            if precio_normalizado_coto is not None:
                precio_efectivo_unidad_normalizada = precio_normalizado_coto
            elif precio_efectivo_total is not None and unidad["amount"] > 0:
                precio_efectivo_unidad_normalizada = (
                    precio_efectivo_total / cantidad / unidad["amount"]
                )
            else:
                precio_efectivo_unidad_normalizada = None

            candidato = {
                "index": i,
                "plu": plu,
                "item_id": item_id,
                "name": item_name,
                "price": item_price,
                "unit_amount": unidad["amount"],
                "unit": unidad["unit"],
                "promos": promos,
                "coto_normalized_price": precio_normalizado_coto,
                "effective_total_price": precio_efectivo_total,
                "effective_price_per_normalized_unit": precio_efectivo_unidad_normalizada,
                "raw_text": texto[:1200]
            }

            print("\n------")
            print(json.dumps(candidato, ensure_ascii=False, indent=2))

            candidatos.append(candidato)

        except Exception as e:
            print("⚠️ Error leyendo candidato:", e)

    return candidatos