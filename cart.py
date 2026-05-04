def limpiar_carrito(page):
    print("🧹 Abriendo carrito...")

    page.goto("https://www.cotodigital.com.ar/sitios/cdigi/carrito")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3000)

    if page.locator("text=No tiene ningún artículo").count() > 0:
        print("✅ Carrito ya vacío")
        return

    vaciar = page.locator("text=/Vaciar Carro/i").first

    if vaciar.count() == 0:
        print("⚠️ No encontré Vaciar Carro")
        return

    vaciar.click()
    page.wait_for_timeout(1500)

    confirmar = page.locator("text=/Si, vaciar|Sí, vaciar/i").first
    confirmar.wait_for(state="visible", timeout=10000)
    confirmar.click()

    page.wait_for_timeout(2500)
    print("✅ Carrito vaciado")