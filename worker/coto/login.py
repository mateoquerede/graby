"""
Login helper that accepts credentials as parameters instead of
reading them from settings.json.
"""

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def login_with_credentials(page, email: str, password: str):
    page.wait_for_load_state("domcontentloaded")
    page.locator("text=Ingresar").first.click()
    page.wait_for_selector('input[type="text"]', timeout=20000)

    page.fill('input[type="text"]', email)
    page.fill('input[type="password"]', password)
    page.keyboard.press("Enter")

    error_message = "Alguno de los datos ingresados no es correcto"
    error_banner = page.get_by_text(error_message, exact=False)

    try:
        error_banner.wait_for(state="visible", timeout=5000)
    except PlaywrightTimeoutError:
        page.locator("text=Ingresar").first.wait_for(state="hidden", timeout=10000)
    else:
        raise ValueError("Credenciales inválidas")
