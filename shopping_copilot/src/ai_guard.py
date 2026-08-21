"""Deterministic safety and cost limits for Ollama requests."""

import re

from shopping_copilot.src.config import (
    MAX_AI_CANDIDATES,
    MAX_AI_ITEMS,
    MAX_AI_PROMPT_CHARS,
    MAX_AI_QUANTITY,
)


SHOPPING_TERMS = {
    "agua", "alimento", "arroz", "bebida", "bizcocho", "branca", "cafe", "carrito",
    "carne", "cerveza", "chocolate", "compra", "comprar", "condimento",
    "desodorante", "detergente", "dulce", "fideos", "galleta", "gaseosa",
    "fernet", "harina", "higiene", "huevo", "jabon", "jugo", "leche",
    "limpieza", "manteca", "mayonesa", "pan", "papel", "pasta", "pollo",
    "producto", "queso", "sal", "shampoo", "supermercado", "vino", "yogur",
    "yerba",
}
INJECTION_PATTERNS = (
    r"\b(ignore|ignora|olvida|forget|disregard)\b.{0,40}\b(instrucciones?|rules?|reglas?)\b",
    r"\b(system|developer|assistant)\s*:",
    r"\b(prompt|instrucciones?)\s+(injection|inyeccion|override|sobreescrib)",
    r"\b(exec|execute|ejecuta|python|powershell|shell|comando)\b",
)


def _tokens(value):
    return set(re.findall(r"[a-záéíóúüñ0-9]+", str(value or "").lower()))


def validate_ai_input(text, *, max_chars=MAX_AI_PROMPT_CHARS, require_shopping_terms=True):
    """Reject malformed, unrelated, or prompt-injection-like user input."""
    value = str(text or "").strip()
    if not value:
        raise ValueError("El pedido está vacío.")
    if len(value) > max_chars:
        raise ValueError(f"El pedido supera el límite de {max_chars} caracteres.")
    if any(re.search(pattern, value, re.IGNORECASE | re.DOTALL) for pattern in INJECTION_PATTERNS):
        raise ValueError("El pedido contiene instrucciones no permitidas.")

    tokens = _tokens(value)
    if require_shopping_terms and not (tokens & SHOPPING_TERMS):
        raise ValueError("Solo puedo ayudarte a armar un carrito de compras.")
    return value


def validate_item_limits(items):
    if len(items) > MAX_AI_ITEMS:
        raise ValueError(f"El pedido no puede superar {MAX_AI_ITEMS} productos.")
    for item in items:
        quantity = float(item.get("quantity", 0))
        if quantity > MAX_AI_QUANTITY:
            raise ValueError(f"La cantidad máxima por producto es {MAX_AI_QUANTITY}.")
    return items


def limit_candidates(candidates):
    return list(candidates)[:MAX_AI_CANDIDATES]
