"""
Search module

Handles product search functionality on Coto Digital website.
"""

def search_product(page, query):
    print(f"🔎 Searching: {query}")

    page.goto("https://www.cotodigital.com.ar/sitios/cdigi/nuevositio")
    page.wait_for_load_state("domcontentloaded")

    buscador = page.get_by_placeholder("¿Qué querés comprar hoy?")
    buscador.wait_for(state="visible", timeout=20000)

    buscador.click()
    buscador.fill("")
    buscador.fill(query)
    buscador.press("Enter")

    page.wait_for_load_state("networkidle")
    page.locator("button:has-text('Agregar')").first.wait_for(
        state="visible", timeout=12000
    )

    print("✅ Results loaded")


def sort_by_lowest_price(page):
    try:
        filtro = page.locator("select").first

        if filtro.count() > 0:
            filtro.select_option(label="Precio: de menor a mayor")
            print("💰 Sorted by lowest price")
            page.wait_for_load_state("networkidle")
            page.locator("button:has-text('Agregar')").first.wait_for(
                state="visible", timeout=10000
            )

    except Exception as e:
        print("⚠️ Could not sort:", e)