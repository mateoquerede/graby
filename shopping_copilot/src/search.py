"""
Search module

Handles product search functionality on Coto Digital website.
"""

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