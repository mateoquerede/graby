"""
Main entry point for the Coto Bot application.

This script automates the process of shopping on Coto Digital:
- Loads product list from lista.json
- Plans search queries using AI
- Logs into the website
- Clears the cart
- Searches and adds products to the cart
- Navigates to the cart for manual checkout
"""

from playwright.sync_api import sync_playwright
from shopping_copilot.src.planner import plan
from shopping_copilot.src.search import buscar_producto
from shopping_copilot.src.add_product import agregar_producto
from shopping_copilot.src.login import login
from shopping_copilot.src.cart import limpiar_carrito
from shopping_copilot.src.config import load_lista, load_settings
from shopping_copilot.src.grocy_client import GrocyClient

def cargar_tasks():
    settings = load_settings()
    grocy_cfg = settings.get("grocy", {})

    if grocy_cfg.get("enabled"):
        client = GrocyClient(
            base_url=grocy_cfg["base_url"],
            api_key=grocy_cfg["api_key"]
        )

        raw_tasks = client.build_tasks_from_shopping_list(
            list_id=grocy_cfg.get("list_id")
        )

        print(f"🧾 Raw tasks desde Grocy: {len(raw_tasks)}")

        tasks = plan(raw_tasks)

        print(f"🧠 Productos desde Grocy: {len(tasks)}")

        return tasks

    productos = load_lista()
    tasks = plan(productos)

    print(f"🧾 Productos desde lista.json: {len(tasks)}")

    return tasks


def main():
    tasks = cargar_tasks()

    if not tasks:
        print("No hay productos para comprar")
        return

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.cotodigital.com.ar")

        login(page)
        limpiar_carrito(page)

        for t in tasks:
            try:
                buscar_producto(page, t["query"])
                agregar_producto(
                    page,
                    t["cantidad"],
                    producto_pedido=t["query"]
                )
            except Exception as e:
                print(f"❌ Falló {t}: {e}")

        print("🛒 Todo agregado")

        page.goto("https://www.cotodigital.com.ar/sitios/cdigi/carrito")

        input("Pagá manualmente y ENTER para cerrar")


if __name__ == "__main__":
    main()