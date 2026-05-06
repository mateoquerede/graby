import json
import math
from datetime import date, datetime
from pathlib import Path
import requests
from consumption_helper.src.shared_config import (
    load_settings,
    load_consumption_rules
)

ROOT_DIR = Path(__file__).resolve().parents[1]

STATE_PATH = ROOT_DIR / "consumption_state.json"


def load_json(path, default=None):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class GrocyAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "GROCY-API-KEY": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get(self, path):
        r = requests.get(
            f"{self.base_url}{path}",
            headers=self.headers,
            timeout=20
        )
        r.raise_for_status()
        return r.json()

    def post(self, path, payload):
        r = requests.post(
            f"{self.base_url}{path}",
            headers=self.headers,
            json=payload,
            timeout=20
        )
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return None
        
    def put(self, path, payload):
        r = requests.put(
            f"{self.base_url}{path}",
            headers=self.headers,
            json=payload,
            timeout=20
        )
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return None

    def get_stock_entry(self, product_id):
        return self.get(f"/api/stock/products/{product_id}")

    def consume_product(self, product_id, amount):
        payload = {
            "amount": amount,
            "transaction_type": "consume",
            "spoiled": False
        }

        return self.post(
            f"/api/stock/products/{product_id}/consume",
            payload
        )

    def add_to_shopping_list(self, product_id, amount, shopping_list_id=1):
        # 1) Grocy agrega el producto a la lista
        result = self.post(
            "/api/stock/shoppinglist/add-product",
            {
                "product_id": product_id,
                "amount": amount,
                "shopping_list_id": shopping_list_id
            }
        )

        # 2) Buscamos la entrada creada/existente
        entries = self.get("/api/objects/shopping_list")

        matching = [
            e for e in entries
            if int(e.get("product_id")) == int(product_id)
            and int(e.get("shopping_list_id")) == int(shopping_list_id)
            and e.get("done") in ["0", 0, False, None]
        ]

        if not matching:
            return result

        entry = matching[-1]
        entry_id = entry["id"]

        # 3) Forzamos la cantidad correcta
        entry["amount"] = amount

        return self.put(
            f"/api/objects/shopping_list/{entry_id}",
            entry
        )


def today_iso():
    return date.today().isoformat()


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_current_stock_amount(stock_entry):
    """
    Grocy suele devolver 'stock_amount' en /api/stock/products/{id}.
    Dejamos fallback por si cambia o viene como string.
    """
    value = (
        stock_entry.get("stock_amount")
        or stock_entry.get("amount")
        or 0
    )

    try:
        return float(value)
    except Exception:
        return 0.0


def calculate_consumption_since_last_run(rule, last_date):
    today = date.today()

    if last_date is None:
        return 0.0, 0

    days_passed = (today - last_date).days

    if days_passed <= 0:
        return 0.0, days_passed

    consume_amount = float(rule["consume_amount"])
    consume_every_days = float(rule["consume_every_days"])

    daily_rate = consume_amount / consume_every_days

    estimated_consumption = days_passed * daily_rate

    return estimated_consumption, days_passed


def calculate_days_left(stock_amount, rule):
    consume_amount = float(rule["consume_amount"])
    consume_every_days = float(rule["consume_every_days"])

    daily_rate = consume_amount / consume_every_days

    if daily_rate <= 0:
        return math.inf

    return stock_amount / daily_rate


def should_add_to_shopping_list(estimated_stock, days_left, rule, global_settings):
    min_stock = float(rule.get("min_stock", 0))

    min_days_until_restock = float(
        rule.get(
            "min_days_until_restock",
            global_settings.get("min_days_until_restock", 3)
        )
    )

    return (
        estimated_stock <= min_stock
        or days_left <= min_days_until_restock
    )


def sync_consumption():
    settings = load_settings()
    grocy_cfg = settings["grocy"]

    if not grocy_cfg.get("enabled"):
        raise RuntimeError("Grocy está deshabilitado en settings.json")

    rules = load_consumption_rules()

    if not rules:
        raise RuntimeError("No existe consumption_rules.json")

    global_settings = rules.get("settings", {})
    products = rules.get("products", {})

    dry_run = bool(global_settings.get("dry_run", True))
    shopping_list_id = global_settings.get("shopping_list_id", 1)

    state = load_json(STATE_PATH, default={"products": {}})

    api = GrocyAPI(
        base_url=grocy_cfg["base_url"],
        api_key=grocy_cfg["api_key"]
    )

    print("🔄 Sync consumo estimado")
    print("Dry run:", dry_run)

    for name, rule in products.items():
        product_id = rule["grocy_product_id"]

        product_state = state["products"].get(str(product_id), {})

        last_run_raw = product_state.get("last_consumption_calc_date")
        last_run_date = parse_date(last_run_raw) if last_run_raw else None

        stock_entry = api.get_stock_entry(product_id)
        current_stock = get_current_stock_amount(stock_entry)

        estimated_consumption, days_passed = calculate_consumption_since_last_run(
            rule,
            last_run_date
        )

        # Consumimos solo unidades enteras para evitar fracciones raras en Grocy
        consume_units = min(
            math.floor(estimated_consumption),
            math.floor(current_stock)
        )
        
        if math.floor(estimated_consumption) > current_stock:
            print("⚠️ Stock insuficiente para consumir todo lo estimado")

        estimated_stock_after_consumption = max(
            current_stock - consume_units,
            0
        )

        days_left = calculate_days_left(
            estimated_stock_after_consumption,
            rule
        )

        print("\n----------------")
        print("Producto:", name)
        print("Grocy ID:", product_id)
        print("Stock actual Grocy:", current_stock)
        print("Último cálculo:", last_run_raw)
        print("Días pasados:", days_passed)
        print("Consumo estimado:", estimated_consumption)
        print("Consumo a registrar:", consume_units)
        print("Stock estimado post consumo:", estimated_stock_after_consumption)
        print("Días restantes:", round(days_left, 2))

        if consume_units > 0:
            if dry_run:
                print(f"DRY RUN: consumiría {consume_units}")
            else:
                api.consume_product(product_id, consume_units)
                print(f"✅ Consumido en Grocy: {consume_units}")

        add_to_list = should_add_to_shopping_list(
            estimated_stock_after_consumption,
            days_left,
            rule,
            global_settings
        )

        if add_to_list:
            buy_amount = float(rule.get("buy_amount", 1))

            if dry_run:
                print(f"DRY RUN: agregaría a shopping list x{buy_amount}")
            else:
                api.add_to_shopping_list(
                    product_id=product_id,
                    amount=buy_amount,
                    shopping_list_id=shopping_list_id
                )
                print(f"🛒 Agregado a shopping list x{buy_amount}")
        else:
            print("✅ No necesita compra")

        product_state["last_consumption_calc_date"] = today_iso()
        product_state["last_estimated_stock"] = estimated_stock_after_consumption
        product_state["last_days_left"] = days_left

        state["products"][str(product_id)] = product_state

    if not dry_run:
        save_json(STATE_PATH, state)
        print("\n💾 Estado actualizado")
    else:
        print("\nDRY RUN: estado no actualizado")


if __name__ == "__main__":
    sync_consumption()