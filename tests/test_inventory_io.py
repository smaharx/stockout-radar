"""Tests for inventory template creation and input loading."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from stockout_radar.inventory import InventoryInputError
from stockout_radar.inventory_io import (
    build_inventory_template,
    load_inventory_inputs,
    save_inventory_template,
)


class InventoryIOTests(unittest.TestCase):

    def test_template_contains_unique_product_codes(self):
        template = build_inventory_template(
            ["10002", "10080", "10002", None, "10120"]
        )

        self.assertEqual(
            template["StockCode"].tolist(),
            ["10002", "10080", "10120"],
        )
        self.assertEqual(len(template), 3)
        self.assertTrue(
            template[
                ["current_stock", "lead_time_days", "safety_stock"]
            ].isna().all().all()
        )

    def test_template_can_be_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.csv"

            save_inventory_template(["10002", "10080"], path)

            self.assertTrue(path.is_file())

            saved = pd.read_csv(
                path,
                dtype={"StockCode": "string"},
            )
            self.assertEqual(len(saved), 2)

    def test_loader_ignores_rows_with_all_inventory_fields_blank(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.csv"

            pd.DataFrame({
                "StockCode": ["10002", "10080"],
                "current_stock": [50, None],
                "lead_time_days": [7, None],
                "safety_stock": [10, None],
            }).to_csv(path, index=False)

            result = load_inventory_inputs(path)

            self.assertEqual(len(result), 1)
            self.assertEqual(result.loc[0, "StockCode"], "10002")

    def test_loader_rejects_a_completely_blank_template(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.csv"

            build_inventory_template(["10002"]).to_csv(
                path,
                index=False,
            )

            with self.assertRaises(InventoryInputError):
                load_inventory_inputs(path)


if __name__ == "__main__":
    unittest.main()
