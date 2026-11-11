"""Reproducible feature engineering for Stockout Radar."""

from __future__ import annotations

import numpy as np
import pandas as pd

from stockout_radar.schema import FEATURE_COLUMNS, TARGET_COLUMN


PANEL_COLUMNS = ("StockCode", "week", "units", "orders", "avg_price")


class FeatureEngineeringError(ValueError):
    """Raised when weekly sales data cannot be used for feature generation."""


def _validate_weekly_panel(weekly_panel: pd.DataFrame) -> pd.DataFrame:
    """Validate and sort the product-level weekly sales panel."""

    if not isinstance(weekly_panel, pd.DataFrame):
        raise FeatureEngineeringError(
            "Weekly panel must be a pandas DataFrame."
        )

    missing = [
        column for column in PANEL_COLUMNS
        if column not in weekly_panel.columns
    ]
    if missing:
        raise FeatureEngineeringError(
            f"Weekly panel is missing required columns: {missing}"
        )

    panel = weekly_panel.loc[:, list(PANEL_COLUMNS)].copy()

    if panel.empty:
        raise FeatureEngineeringError("Weekly panel contains no records.")

    if panel["StockCode"].isna().any():
        raise FeatureEngineeringError("StockCode contains missing values.")

    panel["StockCode"] = panel["StockCode"].astype("string")
    panel["week"] = pd.to_datetime(panel["week"], errors="coerce")

    if panel["week"].isna().any():
        raise FeatureEngineeringError(
            "Week contains missing or invalid dates."
        )

    for column in ("units", "orders", "avg_price"):
        original = panel[column]
        converted = pd.to_numeric(original, errors="coerce")

        invalid = original.notna() & converted.isna()
        if invalid.any():
            raise FeatureEngineeringError(
                f"Column '{column}' contains non-numeric values."
            )

        panel[column] = converted

    values = panel[["units", "orders", "avg_price"]].to_numpy(
        dtype=float
    )

    if not np.isfinite(values).all():
        raise FeatureEngineeringError(
            "Weekly sales data contains missing or infinite numeric values."
        )

    panel = panel.sort_values(
        ["StockCode", "week"]
    ).reset_index(drop=True)

    if panel.duplicated(["StockCode", "week"]).any():
        raise FeatureEngineeringError(
            "Duplicate StockCode/week combinations were found."
        )

    intervals = panel.groupby(
        "StockCode", sort=False
    )["week"].diff()

    irregular = intervals.notna() & (
        intervals != pd.Timedelta(days=7)
    )

    if irregular.any():
        raise FeatureEngineeringError(
            "Weekly history has missing or irregular seven-day intervals. "
            "Resolve these gaps before generating features."
        )

    return panel


def _compute_features(
    panel: pd.DataFrame,
    *,
    include_target: bool = False,
) -> pd.DataFrame:
    """Compute features from an already validated, sorted panel."""

    groups = panel.groupby("StockCode", sort=False)
    result = panel[["StockCode", "week"]].copy()

    for lag in (1, 2, 4):
        result[f"units_lag{lag}"] = groups["units"].shift(lag)

    for window in (4, 8):
        result[f"units_mean{window}"] = groups["units"].transform(
            lambda values: values.shift(1).rolling(
                window, min_periods=window
            ).mean()
        )

        result[f"units_std{window}"] = groups["units"].transform(
            lambda values: values.shift(1).rolling(
                window, min_periods=window
            ).std()
        )

    result["orders_lag1"] = groups["orders"].shift(1)

    result["orders4"] = groups["orders"].transform(
        lambda values: values.shift(1).rolling(
            4, min_periods=4
        ).sum()
    )

    result["price_lag1"] = groups["avg_price"].shift(1)

    result["price_change4"] = (
        groups["avg_price"].shift(1)
        / groups["avg_price"].shift(5)
        - 1
    )

    result["trend_ratio"] = (
        (result["units_mean4"] + 1)
        / (result["units_mean8"] + 1)
    )

    result["week_of_year"] = (
        panel["week"].dt.isocalendar().week.astype("int64")
    )

    result["month"] = panel["week"].dt.month

    christmas_this_year = pd.to_datetime(
        panel["week"].dt.year.astype(str) + "-12-25"
    )
    christmas_next_year = (
        christmas_this_year + pd.DateOffset(years=1)
    )

    christmas = christmas_this_year.where(
        panel["week"] <= christmas_this_year,
        christmas_next_year,
    )

    result["weeks_to_xmas"] = (
        (christmas - panel["week"]).dt.days // 7
    )

    first_week = groups["week"].transform("min")

    result["product_age"] = (
        (panel["week"] - first_week).dt.days // 7
    )

    result = result[
        ["StockCode", "week", *FEATURE_COLUMNS]
    ]

    if include_target:
        result[TARGET_COLUMN] = (
            groups["units"].shift(0)
            + groups["units"].shift(-1)
            + groups["units"].shift(-2)
            + groups["units"].shift(-3)
        )

    return result


def build_feature_table(
    weekly_panel: pd.DataFrame,
    *,
    include_target: bool = False,
) -> pd.DataFrame:
    """
    Generate historical model features.

    At week t, features use sales information through week t-1.
    If requested, the target is sales in weeks t, t+1, t+2 and t+3.
    """

    panel = _validate_weekly_panel(weekly_panel)
    return _compute_features(panel, include_target=include_target)


def latest_feature_rows(weekly_panel: pd.DataFrame) -> pd.DataFrame:
    """
    Generate one inference row per product for the next unseen week.

    The latest observed week becomes units_lag1. The forecast begins
    in the following week and covers that week plus the next three.
    """

    panel = _validate_weekly_panel(weekly_panel)

    last_rows = (
        panel.groupby("StockCode", sort=False)
        .tail(1)
        .copy()
    )

    forecast_rows = last_rows.copy()
    forecast_rows["week"] = (
        forecast_rows["week"] + pd.Timedelta(days=7)
    )

    # Placeholder values are safe: feature calculations for the
    # forecast row use only earlier rows through groupby shifts.
    forecast_rows[["units", "orders", "avg_price"]] = np.nan

    combined = pd.concat(
        [panel, forecast_rows],
        ignore_index=True,
    ).sort_values(
        ["StockCode", "week"]
    ).reset_index(drop=True)

    generated = _compute_features(combined)

    forecast_keys = forecast_rows[["StockCode", "week"]].rename(
        columns={"week": "forecast_start_week"}
    )

    latest = generated.merge(
        forecast_keys.rename(
            columns={"forecast_start_week": "week"}
        ),
        on=["StockCode", "week"],
        how="inner",
        validate="one_to_one",
    )

    history_dates = last_rows[
        ["StockCode", "week"]
    ].rename(
        columns={"week": "history_through_week"}
    )

    latest = latest.merge(
        history_dates,
        on="StockCode",
        how="left",
        validate="one_to_one",
    )

    latest = latest.rename(columns={"week": "forecast_start_week"})

    return latest[
        [
            "StockCode",
            "history_through_week",
            "forecast_start_week",
            *FEATURE_COLUMNS,
        ]
    ].sort_values("StockCode").reset_index(drop=True)
