"""
Login module

Handles authentication to Coto Digital website using credentials from settings.json.
"""

import time
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from shared.shared_config import load_settings

def login(page):

    settings = load_settings()
    
    print("🔐 Logging in...")

    page.wait_for_load_state("domcontentloaded")

    page.locator("text=Ingresar").first.click()

    page.wait_for_selector('input[type="text"]', timeout=20000)

    page.fill('input[type="text"]', settings["coto"]["email"])
    page.fill('input[type="password"]', settings["coto"]["password"])

    page.keyboard.press("Enter")

    error_message = "Alguno de los datos ingresados no es correcto"
    error_banner = page.get_by_text(error_message, exact=False)

    try:
        error_banner.wait_for(state="visible", timeout=5000)
    except PlaywrightTimeoutError:
        time.sleep(3)
    else:
        raise ValueError(f"Credenciales Coto inválidas: {error_message}")

    print("✅ Logged in")