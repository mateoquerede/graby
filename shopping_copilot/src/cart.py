"""
Cart management module

Provides functionality to clear the shopping cart on Coto Digital.
"""

import re
import unicodedata


def should_clear_cart(message):
    """Return True only for an explicit request to empty the existing cart."""
    normalized = unicodedata.normalize("NFD", str(message or "").lower())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if re.search(r"\b(no|nunca)\s+(borres|vacias|limpies|elimines)\b", normalized):
        return False

    return bool(re.search(
        r"\b("
        r"(?:borrar|borra|borre|vaciar|vacia|vacie|limpiar|limpia|limpie|"
        r"eliminar|elimina|elimine)\s+(?:el\s+|mi\s+|el\s+mi\s+)?carrito"
        r"|"
        r"(?:borrar|borra|borre|vaciar|vacia|vacie|limpiar|limpia|limpie|"
        r"eliminar|elimina|elimine)\s+todo\s+(?:del|el)\s+carrito"
        r"|"
        r"(?:carrito)\s+(?:vacio|vacia|limpio|limpia|borrado|eliminado)"
        r"|"
        r"eliminar\s+todo\s+del\s+carrito"
        r")\b",
        normalized,
    ))


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