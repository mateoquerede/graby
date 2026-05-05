import json
import re
from evaluator import evaluar_producto_con_ia

with open("bloqueados.json", "r", encoding="utf-8") as f:
    BLOQUEADOS = json.load(f)

with open("rules.json", "r", encoding="utf-8") as f:
    RULES = json.load(f)


def buscar_producto(page, query):
    print(f"🔎 Buscando: {query}")

    page.goto("https://www.cotodigital.com.ar/sitios/cdigi/nuevositio")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3000)

    buscador = page.get_by_placeholder("¿Qué querés comprar hoy?")
    buscador.wait_for(state="visible", timeout=20000)

    buscador.click()
    buscador.fill("")
    buscador.fill(query)
    buscador.press("Enter")

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)

    print("✅ Resultados cargados")


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


def ordenar_menor_precio(page):
    try:
        filtro = page.locator("select").first

        if filtro.count() > 0:
            filtro.select_option(label="Precio: de menor a mayor")
            print("💰 Ordenado por menor precio")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(4000)

    except Exception as e:
        print("⚠️ No pude ordenar:", e)


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