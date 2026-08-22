"""Dedicated OpenRouter client for JSON LLM requests."""

import os

import httpx


_USAGE_EVENTS = []


def drain_usage_events():
    """Return usage reported by successful requests since the last drain."""
    events = list(_USAGE_EVENTS)
    del _USAGE_EVENTS[:]
    return events


class LLMServiceError(RuntimeError):
    """Raised when every configured model fails to produce a response."""


class OpenRouterClient:
    """Call OpenRouter using worker-side configuration and model fallbacks.

    The API key is read from the worker environment by default. The optional
    constructor argument is only useful for isolated tests or server-side
    callers; it is never supplied by the frontend.
    """

    def __init__(self, api_key=None, model=None, fallback_models=None, base_url=None, timeout=None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.model = model or os.environ.get("OPENROUTER_MODEL", "")
        configured = os.environ.get("OPENROUTER_FALLBACK_MODELS", "")
        single = os.environ.get("OPENROUTER_FALLBACK_MODEL", "")
        env_fallbacks = [item.strip() for item in configured.split(",") + [single] if item.strip()]
        self.fallback_models = fallback_models if fallback_models is not None else env_fallbacks
        self.base_url = (base_url or os.environ.get(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )).rstrip("/")
        self.timeout = timeout or float(os.environ.get("OPENROUTER_TIMEOUT", "60"))

    @property
    def models(self):
        return [model for model in [self.model, *self.fallback_models] if model]

    def complete_json(self, messages, *, max_tokens, temperature=0, top_p=None):
        if not self.api_key:
            raise LLMServiceError("OPENROUTER_API_KEY no está configurada.")
        if not self.models:
            raise LLMServiceError("OPENROUTER_MODEL no está configurado.")

        payload = {
            "model": self.models[0],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "reasoning": {"exclude": True, "effort": "low"},
        }
        if top_p is not None:
            payload["top_p"] = top_p

        errors = []
        for model in self.models:
            for attempt in range(2):
                payload["model"] = model
                try:
                    response = httpx.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://heygraby.com",
                            "X-Title": "Graby",
                        },
                        json={**payload},
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    data = response.json()
                    usage = data.get("usage")
                    if isinstance(usage, dict):
                        prompt_tokens = int(usage.get("prompt_tokens") or 0)
                        completion_tokens = int(usage.get("completion_tokens") or 0)
                        _USAGE_EVENTS.append({
                            "model": model,
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": int(
                                usage.get("total_tokens")
                                or prompt_tokens + completion_tokens
                            ),
                            "cost": usage.get("cost"),
                        })
                    message = data["choices"][0]["message"]
                    content = message.get("content")
                    if isinstance(content, list):
                        content = "".join(
                            part.get("text", "") for part in content if isinstance(part, dict)
                        )
                    if not isinstance(content, str) or not content.strip():
                        reasoning = message.get("reasoning")
                        if isinstance(reasoning, str):
                            content = reasoning
                        else:
                            details = message.get("reasoning_details", [])
                            content = "\n".join(
                                item.get("text", "")
                                for item in details
                                if isinstance(item, dict) and item.get("type") == "reasoning.text"
                            )
                    if not isinstance(content, str) or not content.strip():
                        raise ValueError("OpenRouter devolvió contenido vacío.")
                    return content.strip()
                except httpx.HTTPStatusError as exc:
                    detail = exc.response.text[:300].replace("\n", " ")
                    errors.append(f"{model}: HTTP {exc.response.status_code}: {detail}")
                    break
                except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                    errors.append(f"{model} intento {attempt + 1}: {exc}")

        raise LLMServiceError(
            "Todos los modelos de OpenRouter fallaron: " + "; ".join(errors)
        )


# Keep the existing application import stable while exposing the provider-specific
# service name for new callers.
LLMService = OpenRouterClient
