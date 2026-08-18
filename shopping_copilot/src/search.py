"""
Search module

Handles product search functionality on Coto Digital website.
"""

def handle_address_popup(page):
    """Handle address confirmation popup if it appears."""
    try:
        # Wait briefly for popup to appear
        page.wait_for_timeout(1000)
        
        # Try multiple selectors for the popup
        popup_selectors = [
            ".modal",
            ".modal-dialog", 
            "[role='dialog']",
            ".modal-content",
            ".popup"
        ]
        
        for selector in popup_selectors:
            popup = page.locator(selector).first
            if popup.count() > 0 and popup.is_visible(timeout=500):
                # Check if it has address-related text
                popup_text = popup.inner_text(timeout=1000)
                if any(keyword in popup_text.lower() for keyword in ["dirección", "enviar", "entregar", "cambiar"]):
                    # Try to find "Confirmar" button
                    confirm_button = page.get_by_text("Confirmar", exact=False).first
                    if confirm_button.count() > 0 and confirm_button.is_visible(timeout=500):
                        confirm_button.click(timeout=3000)
                        print("✅ Address popup handled - clicked Confirmar")
                        page.wait_for_timeout(1500)
                        return True
    except Exception as e:
        print(f"⚠️ No address popup or could not handle it: {e}")
    
    return False


def search_product(page, query):
    print(f"🔎 Searching: {query}")

    page.goto(
        "https://www.cotodigital.com.ar/sitios/cdigi/nuevositio",
        wait_until="domcontentloaded",
        timeout=45000,
    )

    buscador = page.get_by_placeholder("¿Qué querés comprar hoy?")
    buscador.wait_for(state="visible", timeout=20000)

    buscador.click()
    buscador.fill("")
    buscador.fill(query)
    buscador.press("Enter")

    page.wait_for_load_state("networkidle")
    
    # Handle address popup if it appears
    handle_address_popup(page)
    
    page.locator("button:has-text('Agregar')").first.wait_for(
        state="visible", timeout=12000
    )

    print("✅ Results loaded")


def sort_by_lowest_price(page):
    try:
        handle_address_popup(page)
        
        filtro = page.locator("select").first

        if filtro.count() > 0:
            filtro.select_option(label="Precio: de menor a mayor")
            print("💰 Sorted by lowest price")
            page.wait_for_load_state("networkidle")
            
            handle_address_popup(page)
            
            page.locator("button:has-text('Agregar')").first.wait_for(
                state="visible", timeout=10000
            )

    except Exception as e:
        print("⚠️ Could not sort:", e)