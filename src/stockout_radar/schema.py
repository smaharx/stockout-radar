"""Canonical feature schema for the saved Stockout Radar demand model."""

FEATURE_COLUMNS = (
    "units_lag1",
    "units_lag2",
    "units_lag4",
    "units_mean4",
    "units_std4",
    "units_mean8",
    "units_std8",
    "orders_lag1",
    "orders4",
    "price_lag1",
    "price_change4",
    "trend_ratio",
    "week_of_year",
    "month",
    "weeks_to_xmas",
    "product_age",
)

TARGET_COLUMN = "target"
PREDICTION_COLUMN = "forecast_4week_demand"
