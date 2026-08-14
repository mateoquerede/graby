"""
Cart management module

Provides functionality to clear the shopping cart on Coto Digital.
"""

def clear_cart(page):
    print("🧹 Opening cart...")

    page.goto(
        "https://www.cotodigital.com.ar/sitios/cdigi/carrito",
        wait_until="domcontentloaded",
        timeout=45000,
    )

    if page.locator("text=No tiene ningún artículo").count() > 0:
        print("✅ Cart is already empty")
        return

    empty_button = page.locator("text=/Vaciar Carro/i").first

    if empty_button.count() == 0:
        print("⚠️ Could not find Empty Cart")
        return

    empty_button.click()

    confirm = page.locator("text=/Si, vaciar|Sí, vaciar/i").first
    confirm.wait_for(state="visible", timeout=10000)
    confirm.click()

    page.locator("text=No tiene ningún artículo").first.wait_for(
        state="visible", timeout=10000
    )
    print("✅ Cart emptied")