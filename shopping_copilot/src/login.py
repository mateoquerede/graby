"""
Login module

Handles authentication to Coto Digital website using credentials from settings.json.
"""

import time
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

    time.sleep(3)

    print("✅ Logged in")