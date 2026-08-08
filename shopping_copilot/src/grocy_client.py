import requests

class GrocyClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "GROCY-API-KEY": api_key,
            "Accept": "application/json"
        }

    def get_shopping_list(self, list_id=None):
        url = f"{self.base_url}/api/objects/shopping_list"

        params = {}

        if list_id is not None:
            params["query[]"] = f"shopping_list_id={list_id}"

        r = requests.get(url, headers=self.headers, params=params, timeout=20)
        r.raise_for_status()

        return r.json()

    def get_product(self, product_id):
        url = f"{self.base_url}/api/objects/products/{product_id}"

        r = requests.get(url, headers=self.headers, timeout=20)
        r.raise_for_status()

        return r.json()

    def build_tasks_from_shopping_list(self, list_id=None):
        items = self.get_shopping_list(list_id=list_id)

        tasks = []

        for item in items:
            product_id = item.get("product_id")

            amount = (
                item.get("amount")
                or item.get("product_amount")
                or 1
            )

            note = item.get("note")

            query = None
            category = None

            if product_id:
                try:
                    product = self.get_product(product_id)

                    query = product.get("name")

                    category = (
                        product.get("description")
                        or product.get("location")
                        or None
                    )

                except Exception as e:
                    print(f"⚠️ Could not read Grocy product {product_id}: {e}")

            if not query:
                query = note

            if not query:
                continue

            try:
                quantity = int(float(amount))
            except Exception:
                quantity = 1

            tasks.append({
                "name": query,
                "quantity": max(quantity, 1),

                # semantic hints
                "category": category,
                "query_hint": query,

                # metadata
                "source": "grocy",
                "grocy_product_id": product_id
            })

        return tasks