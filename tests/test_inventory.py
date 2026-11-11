"""Tests for inventory risk and reorder calculations."""

import unittest

import pandas as pd

from stockout_radar.inventory import (
    InventoryInputError,
    assess_inventory,
)


def sample_forecasts():
    return pd.DataFrame({
        "StockCode": ["PRODUCT-A", "PRODUCT-B", "PRODUCT-C"],
        "forecast_4week_demand": [280.0, 140.0, 140.0],
        "forecast_horizon_weeks": [4, 4, 4],
    })


def sample_inventory():
    return pd.DataFrame({
        "StockCode": ["PRODUCT-A", "PRODUCT-B", "PRODUCT-C"],
        "current_stock": [30, 80, 200],
        "lead_time_days": [7, 7, 7],
        "safety_stock": [10, 5, 5],
    })


class InventoryAssessmentTests(unittest.TestCase):

    def test_reorder_point_and_order_quantity(self):
        result = assess_inventory(
            sample_forecasts(),
            sample_inventory(),
        )

        product_a = result.set_index("StockCode").loc["PRODUCT-A"]

        # 280 / 28 = 10 units per day.
        # Lead-time demand = 10 * 7 = 70.
        # Reorder point = 70 + 10 safety stock = 80.
        self.assertAlmostEqual(product_a["average_daily_demand"], 10)
        self.assertAlmostEqual(product_a["estimated_lead_time_demand"], 70)
        self.assertAlmostEqual(product_a["reorder_point"], 80)

        # Target stock = 280 + 10 = 290.
        # Recommended quantity = ceil(290 - 30) = 260.
        self.assertAlmostEqual(product_a["target_stock_level"], 290)
        self.assertEqual(product_a["recommended_order_qty"], 260)
        self.assertTrue(product_a["reorder_required"])
        self.assertEqual(product_a["risk_status"], "REORDER_NOW")

    def test_watch_and_healthy_statuses(self):
        result = assess_inventory(
            sample_forecasts(),
            sample_inventory(),
        ).set_index("StockCode")

        self.assertEqual(
            result.loc["PRODUCT-B", "risk_status"],
            "WATCH",
        )
        self.assertFalse(
            result.loc["PRODUCT-B", "reorder_required"]
        )

        self.assertEqual(
            result.loc["PRODUCT-C", "risk_status"],
            "HEALTHY",
        )
        self.assertEqual(
            result.loc["PRODUCT-C", "recommended_order_qty"],
            0,
        )

    def test_lead_time_beyond_forecast_horizon_is_rejected(self):
        inventory = sample_inventory()
        inventory.loc[0, "lead_time_days"] = 35

        with self.assertRaises(InventoryInputError):
            assess_inventory(sample_forecasts(), inventory)

    def test_negative_stock_is_rejected(self):
        inventory = sample_inventory()
        inventory.loc[0, "current_stock"] = -5

        with self.assertRaises(InventoryInputError):
            assess_inventory(sample_forecasts(), inventory)

    def test_product_without_forecast_is_rejected(self):
        inventory = sample_inventory()
        inventory.loc[0, "StockCode"] = "UNKNOWN-PRODUCT"

        with self.assertRaises(InventoryInputError):
            assess_inventory(sample_forecasts(), inventory)

    def test_duplicate_inventory_product_is_rejected(self):
        inventory = sample_inventory()
        inventory = pd.concat(
            [inventory, inventory.iloc[[0]]],
            ignore_index=True,
        )

        with self.assertRaises(InventoryInputError):
            assess_inventory(sample_forecasts(), inventory)


if __name__ == "__main__":
    unittest.main()
