"""Tests for Stockout Radar feature engineering."""

import unittest

import numpy as np
import pandas as pd

from stockout_radar.features import (
    FeatureEngineeringError,
    build_feature_table,
    latest_feature_rows,
)
from stockout_radar.schema import FEATURE_COLUMNS, TARGET_COLUMN


def make_weekly_panel(number_of_weeks=14):
    weeks = pd.date_range(
        "2010-01-04",
        periods=number_of_weeks,
        freq="7D",
    )

    return pd.DataFrame({
        "StockCode": ["PRODUCT-A"] * number_of_weeks,
        "week": weeks,
        "units": np.arange(10, 10 + number_of_weeks, dtype=float),
        "orders": np.arange(1, 1 + number_of_weeks, dtype=float),
        "avg_price": np.full(number_of_weeks, 2.5),
    })


class FeatureEngineeringTests(unittest.TestCase):

    def test_generates_all_sixteen_features(self):
        panel = make_weekly_panel()
        features = build_feature_table(panel)

        self.assertEqual(
            list(features.columns),
            ["StockCode", "week", *FEATURE_COLUMNS],
        )
        self.assertEqual(len(features), len(panel))

    def test_lag_and_rolling_features_use_past_data(self):
        panel = make_weekly_panel()
        features = build_feature_table(panel)

        row = features.iloc[8]

        self.assertEqual(row["units_lag1"], 17.0)
        self.assertEqual(row["units_lag2"], 16.0)
        self.assertEqual(row["units_lag4"], 14.0)
        self.assertEqual(row["units_mean4"], 15.5)
        self.assertEqual(row["units_mean8"], 13.5)
        self.assertEqual(row["orders_lag1"], 8.0)
        self.assertEqual(row["orders4"], 26.0)

    def test_target_covers_current_and_next_three_weeks(self):
        panel = make_weekly_panel()
        features = build_feature_table(panel, include_target=True)

        self.assertEqual(
            features.loc[0, TARGET_COLUMN],
            10 + 11 + 12 + 13,
        )
        self.assertTrue(
            pd.isna(features.iloc[-1][TARGET_COLUMN])
        )

    def test_next_forecast_week_uses_latest_observed_week_as_lag1(self):
        panel = make_weekly_panel()
        latest = latest_feature_rows(panel)

        last_observed_week = panel["week"].max()
        forecast_week = last_observed_week + pd.Timedelta(days=7)

        self.assertEqual(len(latest), 1)
        self.assertEqual(
            latest.loc[0, "history_through_week"],
            last_observed_week,
        )
        self.assertEqual(
            latest.loc[0, "forecast_start_week"],
            forecast_week,
        )
        self.assertEqual(
            latest.loc[0, "units_lag1"],
            panel.iloc[-1]["units"],
        )

    def test_latest_rows_returns_one_row_per_product(self):
        panel = make_weekly_panel()

        second_product = panel.copy()
        second_product["StockCode"] = "PRODUCT-B"
        second_product["units"] *= 2

        combined = pd.concat(
            [panel, second_product],
            ignore_index=True,
        )

        latest = latest_feature_rows(combined)

        self.assertEqual(len(latest), 2)
        self.assertEqual(
            set(latest["StockCode"]),
            {"PRODUCT-A", "PRODUCT-B"},
        )
        self.assertTrue(
            (
                latest["forecast_start_week"]
                == panel["week"].max() + pd.Timedelta(days=7)
            ).all()
        )

    def test_irregular_weekly_history_is_rejected(self):
        panel = make_weekly_panel()
        panel = panel.drop(index=5).reset_index(drop=True)

        with self.assertRaises(FeatureEngineeringError):
            build_feature_table(panel)

    def test_duplicate_product_week_is_rejected(self):
        panel = make_weekly_panel()
        panel = pd.concat(
            [panel, panel.iloc[[0]]],
            ignore_index=True,
        )

        with self.assertRaises(FeatureEngineeringError):
            build_feature_table(panel)


if __name__ == "__main__":
    unittest.main()
