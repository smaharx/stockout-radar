import unittest

import numpy as np
import pandas as pd

from stockout_radar.evaluation import build_product_evaluation, calculate_forecast_metrics


class ForecastMetricTests(unittest.TestCase):
    def test_metrics_and_bias_sign(self):
        result = calculate_forecast_metrics([10, 20, 30], [12, 18, 30])
        self.assertEqual(result["observations"], 3)
        self.assertAlmostEqual(result["mae"], 4 / 3)
        self.assertAlmostEqual(result["wape_percent"], 4 / 60 * 100)
        self.assertAlmostEqual(result["total_residual_actual_minus_predicted_units"], 0)
        self.assertAlmostEqual(result["net_forecast_bias_predicted_minus_actual_units"], 0)

    def test_zero_actual_has_undefined_wape(self):
        result = calculate_forecast_metrics([0, 0], [2, 1])
        self.assertIsNone(result["wape_percent"])
        self.assertEqual(result["mae"], 1.5)

    def test_non_finite_pairs_are_excluded(self):
        result = calculate_forecast_metrics([10, np.nan, 20], [8, 3, 22])
        self.assertEqual(result["observations"], 2)
        self.assertAlmostEqual(result["mae"], 2)

    def test_shape_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_forecast_metrics([1, 2], [1])

    def test_product_comparison_against_baseline(self):
        frame = pd.DataFrame({
            "StockCode": ["A", "A", "B", "B"],
            "actual_units": [10, 20, 10, 20],
            "predicted_units": [10, 20, 15, 25],
            "moving_average_baseline_units": [12, 22, 10, 20],
        })
        result = build_product_evaluation(frame).set_index("StockCode")
        self.assertTrue(bool(result.loc["A", "model_better_than_baseline_by_mae"]))
        self.assertFalse(bool(result.loc["B", "model_better_than_baseline_by_mae"]))
        self.assertAlmostEqual(result.loc["A", "mae_improvement_vs_baseline_units"], 2)


if __name__ == "__main__":
    unittest.main()
