import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

module_path = Path(__file__).with_name("add_product.py")
spec = importlib.util.spec_from_file_location("shopping_copilot.src.add_product", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

planner_spec = importlib.util.spec_from_file_location(
    "shopping_copilot.src.planner",
    Path(__file__).with_name("planner.py"),
)
planner = importlib.util.module_from_spec(planner_spec)
planner_spec.loader.exec_module(planner)


class AddProductFlowTests(unittest.TestCase):
    def test_add_product_keeps_search_order_and_does_not_force_lowest_price(self):
        calls = []

        def fake_extract(page, quantity):
            calls.append("extract")
            return []

        with patch.object(module, "extract_candidates", side_effect=fake_extract):
            with self.assertRaisesRegex(Exception, "Unable to extract candidates"):
                module.add_product(object(), 1, requested_product="milk")

        self.assertEqual(calls, ["extract"])


class PlannerPromptParsingTests(unittest.TestCase):
    def test_parse_user_prompt_handles_quantity_and_brand_phrases(self):
        self.assertEqual(
            planner.parse_user_prompt_to_items("1 pan"),
            [{"query": "pan", "quantity": 1}],
        )
        self.assertEqual(
            planner.parse_user_prompt_to_items("1 supremas"),
            [{"query": "suprema", "quantity": 1}],
        )
        self.assertEqual(
            planner.parse_user_prompt_to_items("fernet branca"),
            [{"query": "fernet branca", "quantity": 1}],
        )

    def test_generate_shopping_list_avoids_ai_when_regex_parser_can_handle_prompt(self):
        with patch.object(planner, "ollama") as mocked_ollama:
            result = planner.generate_shopping_list_from_prompt("1 pan")

        self.assertEqual(result, [{"query": "pan", "quantity": 1}])
        mocked_ollama.chat.assert_not_called()

    def test_validate_plan_allows_decimal_quantities(self):
        result = planner.validate_plan([{"query": "harina", "quantity": 1.5}])
        self.assertEqual(result, [{"query": "harina", "quantity": 1.5}])

    def test_unrelated_prompt_is_rejected_before_ollama(self):
        with patch.object(planner, "ollama") as mocked_ollama:
            with self.assertRaisesRegex(ValueError, "carrito"):
                planner.generate_shopping_list_from_prompt("Escribí un poema sobre el mar")

        mocked_ollama.chat.assert_not_called()

    def test_prompt_and_quantity_limits_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "caracteres"):
            planner.generate_shopping_list_from_prompt("pan " + ("x" * 500))
        with self.assertRaisesRegex(ValueError, "máxima"):
            planner.validate_plan([{"query": "pan", "quantity": 51}])


if __name__ == "__main__":
    unittest.main()
