import json
from playwright.sync_api import sync_playwright

from planner import plan
from shopper import buscar_producto, agregar_producto
from login import login
from cart import limpiar_carrito

with open("lista.json") as f:
    productos = json.load(f)

tasks = plan(productos)

with sync_playwright() as p:

    browser = p.firefox.launch(headless=False)
    page = browser.new_page()

    page.goto("https://www.cotodigital.com.ar")

    login(page)

    limpiar_carrito(page)

    for t in tasks:

        buscar_producto(page, t["query"])
        agregar_producto(page, t["cantidad"], producto_pedido=t["query"])

    print("🛒 Todo agregado")

    page.goto("https://www.cotodigital.com.ar/sitios/cdigi/carrito")

    input("Pagá manualmente y ENTER para cerrar")