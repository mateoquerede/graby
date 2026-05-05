"""
Login module

Handles authentication to Coto Digital website using credentials from settings.json.
"""

import json
import time


def login(page):

    settings = json.load(open("../settings.json"))

    print("🔐 Login...")

    page.wait_for_load_state("domcontentloaded")

    page.locator("text=Ingresar").first.click()

    page.wait_for_selector('input[type="text"]', timeout=20000)

    page.fill('input[type="text"]', settings["email"])
    page.fill('input[type="password"]', settings["password"])

    page.keyboard.press("Enter")

    time.sleep(3)

    print("✅ Logueado")