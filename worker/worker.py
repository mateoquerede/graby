"""
Worker entry point.

Polls Redis for purchase jobs, runs the Playwright automation,
and publishes status events back to Redis pub/sub so the
backend can stream them to the frontend via SSE.

Each job payload:
    {
        "job_id": "...",
        "email": "...",
        "password": "...",
        "message": "Quiero comprar leche y huevos"
    }

Credentials are kept only in memory during the job and are
never written to logs, Redis keys, or any persistent store.
"""

import json
import os
import sys
import traceback

import httpx
import redis
from playwright.sync_api import sync_playwright

# Resolve imports: worker/ shares logic from shopping_copilot/src/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from shopping_copilot.src.planner import generate_shopping_list_from_prompt, plan
from shopping_copilot.src.search import search_product
from shopping_copilot.src.cart import clear_cart
from shopping_copilot.src.product_parser import extract_candidates
from shopping_copilot.src.evaluator import evaluate_product_with_ai
from shopping_copilot.src.config import BLOCKED, RULES

from coto.login import login_with_credentials
from coto.add_product import add_product_with_result

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
QUEUE_KEY = "graby:jobs"

CART_URL = "https://www.cotodigital.com.ar/sitios/cdigi/carrito"


def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


def publish(r: redis.Redis, job_id: str, status: str, message: str, **extra):
    payload = {"status": status, "message": message, **extra}
    r.publish(f"graby:events:{job_id}", json.dumps(payload))
    # Also store latest status for polling fallback
    r.hset(f"graby:job:{job_id}", mapping={"status": status, "last_message": message})


def process_job(job: dict):
    r = get_redis()
    job_id = job["job_id"]
    email = job["email"]
    password = job["password"]
    message = job["message"]

    publish(r, job_id, "STARTING", "Iniciando el asistente de compras...")

    try:
        publish(r, job_id, "INTERPRETING_REQUEST", "Interpretando tu pedido...")
        try:
            products = generate_shopping_list_from_prompt(message)
        except httpx.ConnectError:
            publish(
                r, job_id, "FAILED",
                "No se pudo conectar al servicio de IA (Ollama). Verificá que esté disponible e intentá nuevamente.",
            )
            return
        tasks = plan(products)

        if not tasks:
            publish(r, job_id, "FAILED", "No pude interpretar productos en tu pedido.")
            return

        publish(
            r, job_id, "INTERPRETED",
            f"Entendí que necesitás {len(tasks)} producto(s).",
            item_count=len(tasks),
            items=[t["query"] for t in tasks],
        )

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            context = browser.new_context()

            context.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in {"image", "font", "media"}
                else route.continue_(),
            )

            page = context.new_page()
            page.set_default_timeout(15000)
            page.goto("https://www.cotodigital.com.ar")

            publish(r, job_id, "AUTHENTICATING", "Iniciando sesión...")

            try:
                login_with_credentials(page, email, password)
            except ValueError:
                publish(
                    r, job_id, "FAILED",
                    "No pude iniciar sesión. Verificá tus credenciales e intentá nuevamente.",
                )
                context.close()
                browser.close()
                return

            publish(r, job_id, "AUTHENTICATED", "Sesión iniciada correctamente.")

            clear_cart(page)

            selected_items = []

            publish(r, job_id, "SEARCHING_PRODUCTS", "Comenzando la búsqueda de productos...")

            for task in tasks:
                query = task["query"]
                quantity = task["quantity"]

                publish(r, job_id, "SEARCHING_PRODUCTS", f'Buscando "{query}"...')

                try:
                    search_product(page, query)
                    result = add_product_with_result(
                        page, quantity, requested_product=query
                    )

                    if result:
                        publish(
                            r, job_id, "PRODUCT_ADDED",
                            f"Agregué {quantity}x {result['name']} al carrito.",
                            product=result,
                        )
                        selected_items.append(result)
                    else:
                        publish(
                            r, job_id, "PRODUCT_NOT_FOUND",
                            f'⚠️ No encontré un producto que coincida con "{query}".',
                            requested=query,
                        )

                except Exception as exc:
                    publish(
                        r, job_id, "PRODUCT_ERROR",
                        f'⚠️ Error buscando "{query}": {exc}',
                        requested=query,
                    )

            page.goto(CART_URL)
            checkout_url = page.url

            context.close()
            browser.close()

        total = sum(
            (item.get("price", 0) or 0) * item.get("quantity", 1)
            for item in selected_items
        )

        publish(
            r, job_id, "COMPLETED",
            "Tu carrito está listo. Revisá los productos y completá el pago.",
            items=selected_items,
            total=total,
            checkout_url=checkout_url,
        )

    except Exception:
        tb = traceback.format_exc()
        # Log stack trace but never include credentials
        print(f"[worker] Job {job_id} failed:\n{tb}", flush=True)
        publish(
            r, job_id, "FAILED",
            "La automatización se detuvo inesperadamente. No se realizó ningún pago.",
        )


def main():
    r = get_redis()
    print("[worker] Listening for jobs...", flush=True)

    while True:
        # Blocking pop with 5-second timeout so the loop stays alive
        item = r.blpop(QUEUE_KEY, timeout=5)
        if item is None:
            continue

        _, raw = item
        try:
            job = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[worker] Invalid job payload: {raw}", flush=True)
            continue

        job_id = job.get("job_id", "unknown")
        print(f"[worker] Processing job {job_id}", flush=True)
        process_job(job)
        print(f"[worker] Done with job {job_id}", flush=True)


if __name__ == "__main__":
    main()
