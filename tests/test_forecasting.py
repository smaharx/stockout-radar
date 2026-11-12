"""Reproducible tests for the four-week forecasting service."""

import unittest

import numpy as np
import pandas as pd

from stockout_radar.forecasting import (
    DEFAULT_FORECAST_MODEL_PATH,
    DEFAULT_WEEKLY_PANEL_PATH,
    DemandForecastService,
)


def make_synthetic_weekly_panel():
    """Build deterministic weekly history without external dataset files."""

    weeks = pd.date_range(
        start="2021-01-04",
        periods=12,
        freq="W-MON",
    )

    records = []

    for product_index, stock_code in enumerate(("TEST-A", "TEST-B")):
        for week_index, week in enumerate(weeks):
            records.append({
                "StockCode": stock_code,
                "week": week,
                "units": (
                    8
                    + product_index * 3
                    + week_index
                    + (week_index % 3)
                ),
                "orders": 2 + (week_index % 4),
                "avg_price": (
                    1.25
                    + product_index * 0.4
                    + week_index * 0.03
                ),
            })

    return pd.DataFrame(records)


class DemandForecastServiceTests(unittest.TestCase):

    def test_default_paths_point_to_project_artifacts(self):
        # The weekly panel is generated locally and intentionally excluded
        # from Git. Test the configured location, not its local existence.
        self.assertEqual(
            DEFAULT_WEEKLY_PANEL_PATH.name,
            "weekly_panel.csv",
        )
        self.assertEqual(
            DEFAULT_WEEKLY_PANEL_PATH.parent.name,
            "processed",
        )

        # The trained inference artifact is committed and available in CI.
        self.assertTrue(
            DEFAULT_FORECAST_MODEL_PATH.is_file(),
            "The trained forecasting model must be present.",
        )

    def test_generates_next_four_week_forecasts_for_all_products(self):
        panel = make_synthetic_weekly_panel()

        expected_products = panel["StockCode"].nunique()

        service = DemandForecastService()
        forecasts = service.forecast(panel)

        self.assertEqual(len(forecasts), expected_products)
        self.assertEqual(
            forecasts["StockCode"].nunique(),
            expected_products,
        )

        self.assertEqual(
            set(forecasts["forecast_horizon_weeks"]),
            {4},
        )

        self.assertTrue(
            (
                forecasts["forecast_start_week"]
                == forecasts["history_through_week"]
                + pd.Timedelta(days=7)
            ).all()
        )

        self.assertTrue(
            np.isfinite(
                forecasts["raw_model_prediction"].to_numpy(dtype=float)
            ).all()
        )

        self.assertTrue(
            (forecasts["forecast_4week_demand"] >= 0).all()
        )

        np.testing.assert_allclose(
            forecasts["forecast_4week_demand"].to_numpy(dtype=float),
            forecasts["raw_model_prediction"]
            .clip(lower=0)
            .to_numpy(dtype=float),
        )

        self.assertEqual(
            set(forecasts["model_artifact"]),
            {DEFAULT_FORECAST_MODEL_PATH.name},
        )

    def test_forecast_dates_follow_the_latest_available_history(self):
        panel = make_synthetic_weekly_panel()

        forecasts = DemandForecastService().forecast(panel)

        self.assertTrue(
            (
                forecasts["forecast_start_week"]
                > forecasts["history_through_week"]
            ).all()
        )

        self.assertTrue(
            (
                forecasts["history_through_week"]
                <= panel["week"].max()
            ).all()
        )


if __name__ == "__main__":
    unittest.main()
