"""
Main entry point for the Coto Bot application.

This script automates the process of shopping on Coto Digital:
- Loads the product list from shopping_list.json
- Plans search queries using AI
- Logs into the website
- Clears the cart
- Searches and adds products to the cart
- Navigates to the cart for manual checkout
"""

from playwright.sync_api import sync_playwright
from shopping_copilot.src.planner import plan, generate_shopping_list_from_prompt
from shopping_copilot.src.search import search_product
from shopping_copilot.src.add_product import add_product
from shopping_copilot.src.login import login
from shopping_copilot.src.cart import clear_cart
from shopping_copilot.src.config import (
    load_shopping_list,
    load_settings,
    SHOPPING_LIST_PATH,
)
from shopping_copilot.src.grocy_client import GrocyClient

def load_tasks():
    settings = load_settings()
    grocy_cfg = settings.get("grocy", {})

    if grocy_cfg.get("enabled"):
        try:
            client = GrocyClient(
                base_url=grocy_cfg["base_url"],
                api_key=grocy_cfg["api_key"]
            )

            raw_tasks = client.build_tasks_from_shopping_list(
                list_id=grocy_cfg.get("list_id")
            )

            print(f"🧾 Raw tasks from Grocy: {len(raw_tasks)}")

            tasks = plan(raw_tasks)

            print(f"🧠 Products from Grocy: {len(tasks)}")

            return tasks
        except Exception as e:
            print(f"⚠️ Grocy unavailable ({e}), falling back to shopping_list.json")

    if not SHOPPING_LIST_PATH.exists():
        raise FileNotFoundError(
            "shopping_list.json not found. Use prompt in terminal or create shopping_copilot/shopping_list.json"
        )

    products = load_shopping_list()

    tasks = plan(products)

    print(f"🧾 Products from shopping_list.json: {len(tasks)}")

    return tasks


def load_tasks_from_prompt():
    user_prompt = input(
        "Que queres comprar? "
    ).strip()

    if not user_prompt:
        raise ValueError("Shopping prompt cannot be empty")

    products = generate_shopping_list_from_prompt(user_prompt)
    tasks = plan(products)

    print(f"🧾 Products from prompt: {len(tasks)}")

    return tasks


def main():
    try:
        tasks = load_tasks()
    except FileNotFoundError:
        print("⚠️ No Grocy list and shopping_list.json not found. Switching to prompt mode.")
        tasks = load_tasks_from_prompt()

    if not tasks:
        print("No products to buy")
        return

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.cotodigital.com.ar")

        try:
            login(page)
        except ValueError as e:
            print(f"❌ {e}")
            return

        clear_cart(page)

        for t in tasks:
            try:
                search_product(page, t["query"])
                add_product(
                    page,
                    t["quantity"],
                    requested_product=t["query"]
                )
            except Exception as e:
                print(f"❌ Failed {t}: {e}")

        print("🛒 All items added")

        page.goto("https://www.cotodigital.com.ar/sitios/cdigi/carrito")

        input("Complete payment manually and press ENTER to close")


if __name__ == "__main__":
    main()