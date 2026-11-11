"""Integration tests for the Stockout Radar forecasting service."""

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from stockout_radar.forecasting import (
    DEFAULT_FORECAST_MODEL_PATH,
    DEFAULT_WEEKLY_PANEL_PATH,
    DemandForecastService,
)


class DemandForecastServiceTests(unittest.TestCase):

    def test_default_paths_point_to_project_artifacts(self):
        self.assertTrue(DEFAULT_WEEKLY_PANEL_PATH.is_file())
        self.assertTrue(DEFAULT_FORECAST_MODEL_PATH.is_file())

    def test_generates_next_four_week_forecasts_for_all_products(self):
        panel = pd.read_csv(
            DEFAULT_WEEKLY_PANEL_PATH,
            dtype={"StockCode": "string"},
            parse_dates=["week"],
        )

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

        self.assertTrue(
            (
                forecasts["forecast_4week_demand"]
                == forecasts["raw_model_prediction"].clip(lower=0)
            ).all()
        )

        self.assertEqual(
            set(forecasts["model_artifact"]),
            {"stockout_radar_v1.joblib"},
        )

    def test_forecast_dates_follow_the_latest_available_history(self):
        panel = pd.read_csv(
            DEFAULT_WEEKLY_PANEL_PATH,
            dtype={"StockCode": "string"},
            parse_dates=["week"],
        )

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
