"""Login helper for Coto Digital using per-job credentials."""

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def login_with_credentials(page, email: str, password: str):
    page.wait_for_load_state("domcontentloaded")
    page.locator("text=Ingresar").first.click()
    page.wait_for_url("**/ingresar", timeout=20000)

    login_input = page.locator("input[name='login']")
    password_input = page.locator("input[name='password']")
    submit_button = page.locator("button:has-text('Ingresar')").first

    login_input.wait_for(state="visible", timeout=20000)
    password_input.wait_for(state="visible", timeout=20000)

    login_input.fill(email)
    password_input.fill(password)
    submit_button.wait_for(state="visible", timeout=10000)
    submit_button.click()

    error_message = "Alguno de los datos ingresados no es correcto"
    error_banner = page.get_by_text(error_message, exact=False)

    for _ in range(30):
        if error_banner.is_visible():
            raise ValueError("Credenciales inválidas")
        if "/ingresar" not in page.url:
            return
        page.wait_for_timeout(500)

    raise PlaywrightTimeoutError("No pude confirmar inicio de sesión")
