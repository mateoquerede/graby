import importlib.util
import sys
import unittest
import httpx
from pathlib import Path
from unittest.mock import MagicMock, patch

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
llm_spec = importlib.util.spec_from_file_location(
    "shopping_copilot.src.llm_service",
    Path(__file__).with_name("llm_service.py"),
)
llm_service = importlib.util.module_from_spec(llm_spec)
llm_spec.loader.exec_module(llm_service)


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
        self.assertEqual(
            planner.parse_user_prompt_to_items(
                "1kg de supremas, 2 melbas, 3 coca colas 1.5lts"
            ),
            [
                {"query": "suprema", "quantity": 1},
                {"query": "melba", "quantity": 2},
                {"query": "coca cola", "quantity": 3},
            ],
        )

    def test_generate_shopping_list_avoids_ai_when_regex_parser_can_handle_prompt(self):
        with patch.object(planner.LLMService, "complete_json") as mocked_llm:
            result = planner.generate_shopping_list_from_prompt("1 pan")

        self.assertEqual(result, [{"query": "pan", "quantity": 1}])
        mocked_llm.assert_not_called()

    def test_validate_plan_allows_decimal_quantities(self):
        result = planner.validate_plan([{"query": "harina", "quantity": 1.5}])
        self.assertEqual(result, [{"query": "harina", "quantity": 1.5}])

    def test_unrelated_prompt_is_rejected_before_openrouter(self):
        with patch.object(planner.LLMService, "complete_json") as mocked_llm:
            with self.assertRaisesRegex(ValueError, "carrito"):
                planner.generate_shopping_list_from_prompt("Escribí un poema sobre el mar")

        mocked_llm.assert_not_called()

    def test_prompt_and_quantity_limits_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "caracteres"):
            planner.generate_shopping_list_from_prompt("pan " + ("x" * 500))
        with self.assertRaisesRegex(ValueError, "máxima"):
            planner.validate_plan([{"query": "pan", "quantity": 51}])


class LLMServiceTests(unittest.TestCase):
    def test_uses_fallback_model_after_primary_failure(self):
        failed = MagicMock()
        failed.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rate limited",
            request=httpx.Request("POST", "https://openrouter.ai"),
            response=httpx.Response(429),
        )
        succeeded = MagicMock()
        succeeded.raise_for_status.return_value = None
        succeeded.json.return_value = {
            "choices": [{"message": {"content": '{"ok": true}'}}]
        }

        with patch.object(llm_service.httpx, "post", side_effect=[failed, succeeded]) as post:
            result = llm_service.LLMService(
                api_key="key",
                model="free/model",
                fallback_models=["paid/model"],
            ).complete_json([{"role": "user", "content": "test"}], max_tokens=20)

        self.assertEqual(result, '{"ok": true}')
        self.assertEqual([call.kwargs["json"]["model"] for call in post.call_args_list],
                         ["free/model", "paid/model"])

    def test_sends_json_response_format(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": [{"message": {"content": "[]"}}]}

        with patch.object(llm_service.httpx, "post", return_value=response) as post:
            llm_service.LLMService(api_key="key", model="free/model").complete_json(
                [{"role": "user", "content": "test"}], max_tokens=20
            )

        self.assertEqual(post.call_args.kwargs["json"]["response_format"], {"type": "json_object"})

    def test_excludes_model_reasoning_from_response(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": [{"message": {"content": '{"ok": true}'}}]}

        with patch.object(llm_service.httpx, "post", return_value=response) as post:
            llm_service.LLMService(api_key="key", model="free/model").complete_json(
                [{"role": "user", "content": "test"}], max_tokens=20
            )

        self.assertEqual(
            post.call_args.kwargs["json"]["reasoning"],
            {"exclude": True, "effort": "low"},
        )

    def test_uses_reasoning_when_provider_leaves_content_empty(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "",
                    "reasoning_details": [{
                        "type": "reasoning.text",
                        "text": '{"selected_plu":"123","reason":"coincide"}',
                    }],
                }
            }]
        }

        with patch.object(llm_service.httpx, "post", return_value=response):
            result = llm_service.LLMService(
                api_key="key", model="free/model"
            ).complete_json([{"role": "user", "content": "test"}], max_tokens=20)

        self.assertEqual(result, '{"selected_plu":"123","reason":"coincide"}')


if __name__ == "__main__":
    unittest.main()
