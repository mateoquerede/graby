"""
Worker entry point.

Polls Redis for purchase jobs, runs the Coto HTTP APIs,
and publishes status events back to Redis pub/sub so the
backend can stream them to the frontend via SSE/WebSocket.

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

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
QUEUE_KEY = "graby:jobs"

def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


def publish(r: redis.Redis, job_id: str, status: str, message: str, **extra):
    payload = {"type": "status", "status": status, "message": message, **extra}
    r.publish(f"graby:events:{job_id}", json.dumps(payload))
    # Also store latest status for polling fallback
    r.hset(
        f"graby:job:{job_id}",
        mapping={
            "status": status,
            "last_message": message,
            "last_event": json.dumps(payload),
        },
    )

def publish_debug_usage(r: redis.Redis, job_id: str, label: str):
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
    r = get_redis()
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
