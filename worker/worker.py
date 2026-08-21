"""
Worker entry point. Claims PostgreSQL jobs and runs the Coto HTTP APIs.

Each job payload:
    {
        "job_id": "...",
        "email": "...",
        "password": "...",
        "message": "Quiero comprar leche y huevos"
    }

Credentials are used only for the Coto session and never written to logs or
included in worker events.
"""

import os
import sys
import traceback

import httpx

# Resolve imports: worker/ + shopping_copilot/ from repo root
WORKER_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(WORKER_DIR, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, WORKER_DIR)

from shopping_copilot.src.planner import generate_shopping_list_from_prompt, plan
from shopping_copilot.src.llm_service import LLMServiceError, drain_usage_events
from shopping_copilot.src.config import is_debug_enabled
from shopping_copilot.src.search import search_product

from coto.login import login_with_credentials
from coto.add_product import add_product_with_result
from coto.client import CotoClient
from database import claim_job, init_db, publish as publish_job, recover_stale_jobs, wait_for_job


def publish(r, job_id: str, status: str, message: str, **extra):
    publish_job(job_id, status, message, **extra)


def publish_debug_usage(r, job_id: str, label: str):
    if not is_debug_enabled():
        drain_usage_events()
        return

    events = drain_usage_events()
    if not events:
        return

    prompt_tokens = sum(int(event.get("prompt_tokens") or 0) for event in events)
    completion_tokens = sum(int(event.get("completion_tokens") or 0) for event in events)
    total_tokens = sum(int(event.get("total_tokens") or 0) for event in events)
    costs = [float(event["cost"]) for event in events if event.get("cost") is not None]
    details = ", ".join(
        f"{event['model']}: {int(event.get('total_tokens') or 0)} tokens"
        for event in events
    )
    message = (
        f"[DEBUG] {label}: {total_tokens} tokens "
        f"(entrada {prompt_tokens}, salida {completion_tokens})"
    )
    if costs:
        message += f" | costo estimado USD {sum(costs):.6f}"
    publish(
        r,
        job_id,
        "DEBUG_LLM_USAGE",
        message,
        debug=True,
        usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": sum(costs) if costs else None,
            "requests": len(events),
            "details": details,
        },
    )


def process_job(job: dict):
    r = None
    drain_usage_events()
    job_id = job["job_id"]
    email = job["email"]
    password = job["password"]
    message = job["message"]
    publish(r, job_id, "STARTING", "Iniciando el asistente de compras...")

    try:
        publish(r, job_id, "INTERPRETING_REQUEST", "Interpretando tu pedido...")
        try:
            products = generate_shopping_list_from_prompt(message)
            publish_debug_usage(r, job_id, "interpretación del pedido")
        except httpx.ConnectError:
            publish(
                r, job_id, "FAILED",
                "No se pudo conectar al servicio de IA (OpenRouter). Verificá la API key e intentá nuevamente.",
            )
            return
        except LLMServiceError as exc:
            publish(r, job_id, "FAILED", str(exc))
            return
        except ValueError as exc:
            publish(r, job_id, "FAILED", str(exc))
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

        client = CotoClient()
        try:
            client.bootstrap()
            publish(r, job_id, "AUTHENTICATING", "Iniciando sesión...")

            try:
                login_with_credentials(client, email, password)
            except ValueError:
                publish(
                    r, job_id, "FAILED",
                    "No pude iniciar sesión. Verificá tus credenciales e intentá nuevamente.",
                )
                return

            publish(r, job_id, "AUTHENTICATED", "Sesión iniciada correctamente.")
            client.ensure_delivery_address()

            selected_items = []

            publish(r, job_id, "SEARCHING_PRODUCTS", "Comenzando la búsqueda de productos...")

            for task in tasks:
                query = task["query"]
                quantity = task["quantity"]

                drain_usage_events()
                publish(r, job_id, "SEARCHING_PRODUCTS", f'Buscando "{query}"...')

                try:
                    search_payload = search_product(client, query)
                    result = add_product_with_result(
                        client, search_payload, quantity, requested_product=query
                    )
                    publish_debug_usage(r, job_id, f'búsqueda "{query}"')

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
            checkout_url = client.cart_url()
            checkout_url = client.cart_url()
        finally:
            client.close()

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
    init_db()
    recover_stale_jobs()
    print("[worker] Listening for jobs...", flush=True)

    while True:
        recover_stale_jobs()
        job = claim_job()
        if job is None:
            wait_for_job(2)
            continue

        job_id = job["job_id"]
        print(f"[worker] Processing job {job_id}", flush=True)
        process_job(job)
        print(f"[worker] Done with job {job_id}", flush=True)


if __name__ == "__main__":
    main()
