from shopping_copilot.src.config import load_settings
from shopping_copilot.src.grocy_client import GrocyClient

settings = load_settings()
grocy_cfg = settings["grocy"]

client = GrocyClient(
    base_url=grocy_cfg["base_url"],
    api_key=grocy_cfg["api_key"]
)

tasks = client.build_tasks_from_shopping_list(
    list_id=grocy_cfg.get("list_id")
)

for t in tasks:
    print(t)