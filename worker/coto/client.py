"""HTTP client for the Coto Digital APIs."""

import os
import re
from urllib.parse import quote, urljoin

import httpx
from shopping_copilot.src.config import debug_print


class CotoApiError(RuntimeError):
    """Raised when Coto rejects an API request."""


class CotoClient:
    BASE_URL = "https://www.coto.com.ar"
    SEARCH_URL = (
        "https://api.coto.com.ar/api/v1/ms-digital-sitio-bff-web/"
        "api/v1/products/search/{query}"
    )
    ADD_URL = "/rest/model/atg/actors/cCarritoActor/addOrRemoveItemToOrderV2"
    LOGIN_URL = "/rest/model/atg/actors/cProfileActor/login"

    def __init__(self):
        self.http = httpx.Client(
            base_url=self.BASE_URL,
            follow_redirects=True,
            timeout=httpx.Timeout(45.0, connect=15.0),
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        self.dyn_sess_conf = ""
        self.search_api_key = os.environ.get("COTO_SEARCH_API_KEY", "")

    def close(self):
        self.http.close()

    def bootstrap(self):
        debug_print("[Coto bootstrap] init request...")
        response = self.http.post(
            "/rest/model/atg/actors/cProfileActor/init",
            params={"pushSite": "CotoDigital"},
        )
        debug_print(f"[Coto bootstrap] init status={response.status_code}")
        response.raise_for_status()
        confirmation = self.http.post(
            "/rest/model/atg/rest/SessionConfirmationActor/getSessionConfirmationNumber",
            params={"pushSite": "CotoDigital"},
        )
        debug_print(f"[Coto bootstrap] confirmation status={confirmation.status_code}")
        confirmation.raise_for_status()
        payload = confirmation.json()
        debug_print("[Coto bootstrap] confirmation payload:", payload)
        token = payload.get("sessionConfirmationNumber")
        if token is None:
            raise CotoApiError("Coto no devolvió un token de sesión")
        self.dyn_sess_conf = str(token)
        debug_print(f"[Coto bootstrap] dyn_sess_conf={self.dyn_sess_conf}")

    def _actor_url(self, path):
        if not self.dyn_sess_conf:
            self.bootstrap()
        return urljoin(self.BASE_URL, path), {
            "pushSite": "CotoDigital",
            "_dynSessConf": self.dyn_sess_conf,
        }

    def login(self, login: str, password: str):
        debug_print(f"[Coto login] POST {self.LOGIN_URL} (login={login!r}, password_len={len(password)})")
        url, params = self._actor_url(self.LOGIN_URL)
        response = self.http.post(
            url,
            params=params,
            data={"IsAngular": "true", "login": login, "password": password},
        )
        debug_print(f"[Coto login] status={response.status_code}")
        debug_print(f"[Coto login] response text={response.text[:500]!r}")
        response.raise_for_status()
        if not response.text.strip():
            debug_print("[Coto login] empty response body")
            return {}
        try:
            payload = response.json()
        except ValueError as exc:
            debug_print("[Coto login] invalid JSON response")
            raise CotoApiError("Respuesta de login inválida") from exc
        debug_print(f"[Coto login] parsed payload={payload}")
        if str(payload.get("codigoError", "0")) != "0" or payload.get("error"):
            debug_print(f"[Coto login] rejected: codigoError={payload.get('codigoError')} error={payload.get('error')}")
            raise ValueError("Credenciales inválidas")
        if isinstance(payload, dict) and payload.get("success") is False:
            debug_print("[Coto login] rejected: success=false")
            raise ValueError("Credenciales inválidas")
        return payload

    def ensure_delivery_address(self):
        """Select the account's default delivery address for the active order."""
        url, params = self._actor_url(
            "/rest/model/atg/actors/cProfileActor/getDireccionesEntrega"
        )
        response = self.http.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
        debug_print("Coto delivery addresses:", payload)
        addresses = payload.get("domicilios") or []
        default_id = payload.get("defaultShippingAddressId")
        if isinstance(addresses, dict):
            addresses = addresses.get("items") or addresses.get("results") or []
        if not isinstance(addresses, list) or not addresses:
            raise CotoApiError("La cuenta no tiene domicilios de entrega configurados")

        selected = next(
            (
                address for address in addresses
                if isinstance(address, dict)
                and (
                    str(
                        address.get("id")
                        or address.get("ID")
                        or address.get("idDomicilio")
                        or address.get("IDDOMICILIO")
                        or address.get("idDireccion")
                        or address.get("IDDIRECCION")
                    ) == str(default_id)
                )
            ),
            None,
        ) or next(
            (
                address for address in addresses
                if isinstance(address, dict)
                and any(
                    address.get(key) is True
                    or str(address.get(key)).lower() in {"true", "s", "y", "1"}
                    for key in (
                        "selected",
                        "default",
                        "predeterminado",
                        "seleccionado",
                        "SELECCIONADA",
                    )
                )
            ),
            addresses[0],
        )
        if not isinstance(selected, dict):
            raise CotoApiError("Coto devolvió un domicilio inválido")
        address_id = (
            selected.get("id")
            or selected.get("ID")
            or selected.get("idDomicilio")
            or selected.get("IDDOMICILIO")
            or selected.get("idDireccion")
            or selected.get("IDDIRECCION")
            or selected.get("idAddress")
            or selected.get("IDADDRESS")
            or selected.get("address_id")
            or selected.get("codigo")
        )
        if not address_id:
            raise CotoApiError("Coto no devolvió el identificador del domicilio")

        change_url, change_params = self._actor_url(
            "/rest/model/atg/actors/cProfileActor/changeDeliveryAddress"
        )
        change_params["selectedAddress"] = str(address_id)
        changed = self.http.get(
            change_url,
            params=change_params,
        )
        changed.raise_for_status()
        changed_payload = changed.json()
        if str(changed_payload.get("codigoError", "0")) != "0":
            raise CotoApiError(
                changed_payload.get("mensajeError", "No se pudo seleccionar el domicilio")
            )

    def search(self, query: str, store_id: str = "200"):
        if not self.search_api_key:
            self.search_api_key = self._discover_search_api_key()
        response = self.http.get(
            self.SEARCH_URL.format(query=quote(query, safe="")),
            params={
                "key": self.search_api_key,
                "num_results_per_page": 24,
                "pre_filter_expression": '{"name":"store_availability","value":"%s"}' % store_id,
                "c": "cio-fe-web-coto-4.2.0",
                "i": "c153a437-d12d-4053-a41c-444adf91c32d",
                "s": "13",
                "origin_referrer": "/productos/" + query,
                "us": store_id,
            },
        )
        response.raise_for_status()
        return response.json()

    def _discover_search_api_key(self):
        """Read the current Constructor search key from Coto's public bundle."""
        response = self.http.get("/")
        response.raise_for_status()
        scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', response.text)
        for script in scripts:
            bundle = self.http.get(urljoin(str(response.url), script))
            bundle.raise_for_status()
            match = re.search(r"\b(key_[A-Za-z0-9]+)\b", bundle.text)
            if match:
                return match.group(1)
        raise CotoApiError("No se pudo obtener la clave de búsqueda de Coto")

    def add_item(self, product_id: str, sku_id: str, quantity):
        url, params = self._actor_url(self.ADD_URL)
        response = self.http.post(
            url,
            params=params,
            data={
                "cambiaSuc": "true",
                "prodId": product_id,
                "quantity": str(quantity),
                "skuId": sku_id,
                "sucPickUp": "null",
            },
        )
        response.raise_for_status()
        payload = response.json()
        debug_print("Coto add-to-cart response:", payload)
        if str(payload.get("codigoError", "0")) != "0":
            raise CotoApiError(payload.get("mensajeError", "No se pudo agregar el producto"))
        return payload

    def cart_url(self):
        return urljoin(self.BASE_URL, "/sitios/cdigi/carrito")
