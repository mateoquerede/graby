import json
import re

with open("bloqueados.json", "r", encoding="utf-8") as f:
    BLOQUEADOS = json.load(f)


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


def obtener_plu_from_button(btn):
    for nivel in range(1, 12):
        try:
            contenedor = btn.locator(f"xpath=ancestor::*[{nivel}]")
            item_id = contenedor.get_attribute("data-cnstrc-item-id", timeout=1000)

            if item_id:
                match = re.search(r"prod0*([0-9]+)", item_id)
                if match:
                    return match.group(1), contenedor, item_id

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


def click_plus_por_item_id(page, item_id, veces):
    for n in range(veces):
        clicked = page.evaluate(
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

        print("➕ resultado:", clicked)

        if not clicked.get("ok"):
            raise Exception(f"No pude clickear +: {clicked}")

        page.wait_for_timeout(900)


def agregar_producto(page, cantidad):
    print(f"🛒 Agregando {cantidad} unidades")

    try:
        filtro = page.locator("select").first

        if filtro.count() > 0:
            filtro.select_option(label="Precio: de menor a mayor")
            print("💰 Ordenado por menor precio")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(4000)

    except Exception as e:
        print("⚠️ No pude ordenar:", e)

    productos = obtener_botones_agregar(page)

    if productos is None:
        page.screenshot(path="debug_sin_agregar.png", full_page=True)
        raise Exception("No encontré botones Agregar")

    total = productos.count()
    print("📦 Productos encontrados:", total)

    producto_elegido = None
    item_id_elegido = None

    for i in range(total):
        btn = productos.nth(i)

        try:
            plu, card, item_id = obtener_plu_from_button(btn)

            print("\n------")
            print("PLU detectado:", plu)
            print("item_id:", item_id)

            if not plu:
                print("⚠️ No pude detectar PLU")
                continue

            if plu in BLOQUEADOS.get("plu", []):
                print(f"🚫 PLU bloqueado: {plu}")
                continue

            texto = card.inner_text(timeout=2000)
            print(texto[:300])

            producto_elegido = btn
            item_id_elegido = item_id

            print("✅ Producto válido encontrado")
            break

        except Exception as e:
            print("⚠️ Error leyendo producto:", e)

    if producto_elegido is None:
        raise Exception("No encontré producto válido")

    producto_elegido.click()
    print("✅ Producto agregado")

    page.wait_for_timeout(3000)

    if cantidad <= 1:
        return

    print("➕ Ajustando cantidad...")
    click_plus_por_item_id(page, item_id_elegido, cantidad - 1)

    print(f"✅ agregado x{cantidad}")