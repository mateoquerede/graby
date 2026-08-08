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


class AddProductFlowTests(unittest.TestCase):
    def test_add_product_sorts_before_extracting_candidates(self):
        calls = []

        def fake_sort(page):
            calls.append("sort")

        def fake_extract(page, quantity):
            calls.append("extract")
            return []

        with patch.object(module, "sort_by_lowest_price", side_effect=fake_sort):
            with patch.object(module, "extract_candidates", side_effect=fake_extract):
                with self.assertRaisesRegex(Exception, "Unable to extract candidates"):
                    module.add_product(object(), 1, requested_product="milk")

        self.assertEqual(calls, ["sort", "extract"])


if __name__ == "__main__":
    unittest.main()
