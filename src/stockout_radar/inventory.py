"""Inventory risk assessment and reorder recommendations."""

from __future__ import annotations

import numpy as np
import pandas as pd


FORECAST_COLUMNS = (
    "StockCode",
    "forecast_4week_demand",
    "forecast_horizon_weeks",
)

INVENTORY_COLUMNS = (
    "StockCode",
    "current_stock",
    "lead_time_days",
    "safety_stock",
)

FORECAST_HORIZON_DAYS = 28


class InventoryInputError(ValueError):
    """Raised when forecast or inventory inputs are invalid."""


def _validate_numeric(
    frame: pd.DataFrame,
    column: str,
    *,
    minimum: float,
) -> None:
    """Require a finite numeric column at or above a minimum value."""

    original = frame[column]
    converted = pd.to_numeric(original, errors="coerce")

    invalid = original.notna() & converted.isna()
    if invalid.any() or converted.isna().any():
        raise InventoryInputError(
            f"'{column}' must contain numeric values without missing data."
        )

    values = converted.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise InventoryInputError(
            f"'{column}' contains infinite or invalid values."
        )

    if (values < minimum).any():
        raise InventoryInputError(
            f"'{column}' must be greater than or equal to {minimum}."
        )

    frame[column] = converted.astype(float)


def assess_inventory(
    forecasts: pd.DataFrame,
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compare four-week forecasts with user-supplied inventory information.

    Required inventory fields:
      - StockCode
      - current_stock
      - lead_time_days
      - safety_stock

    Lead-time demand is approximated by spreading four-week forecast demand
    evenly over 28 days. Lead times beyond the forecast horizon are rejected.

    This initial version does not account for purchase orders, reservations,
    supplier constraints, or multiple warehouses.
    """

    if not isinstance(forecasts, pd.DataFrame):
        raise InventoryInputError("Forecasts must be a pandas DataFrame.")

    if not isinstance(inventory, pd.DataFrame):
        raise InventoryInputError("Inventory must be a pandas DataFrame.")

    missing_forecast = [
        column for column in FORECAST_COLUMNS
        if column not in forecasts.columns
    ]
    if missing_forecast:
        raise InventoryInputError(
            f"Forecast data is missing columns: {missing_forecast}"
        )

    missing_inventory = [
        column for column in INVENTORY_COLUMNS
        if column not in inventory.columns
    ]
    if missing_inventory:
        raise InventoryInputError(
            f"Inventory data is missing columns: {missing_inventory}"
        )

    forecast_data = forecasts.loc[
        :, list(FORECAST_COLUMNS)
    ].copy()

    inventory_data = inventory.loc[
        :, list(INVENTORY_COLUMNS)
    ].copy()

    for frame, name in (
        (forecast_data, "forecast"),
        (inventory_data, "inventory"),
    ):
        if frame["StockCode"].isna().any():
            raise InventoryInputError(
                f"{name} data contains missing StockCode values."
            )

        frame["StockCode"] = frame["StockCode"].astype("string")

        if frame["StockCode"].duplicated().any():
            raise InventoryInputError(
                f"{name} data contains duplicate StockCode values."
            )

    _validate_numeric(
        forecast_data,
        "forecast_4week_demand",
        minimum=0,
    )
    _validate_numeric(
        forecast_data,
        "forecast_horizon_weeks",
        minimum=0,
    )

    if not (
        forecast_data["forecast_horizon_weeks"] == 4
    ).all():
        raise InventoryInputError(
            "Inventory assessment requires four-week forecasts."
        )

    _validate_numeric(
        inventory_data,
        "current_stock",
        minimum=0,
    )
    _validate_numeric(
        inventory_data,
        "lead_time_days",
        minimum=1,
    )
    _validate_numeric(
        inventory_data,
        "safety_stock",
        minimum=0,
    )

    if not (
        inventory_data["lead_time_days"]
        == np.floor(inventory_data["lead_time_days"])
    ).all():
        raise InventoryInputError(
            "Lead time must be expressed as a whole number of days."
        )

    if (
        inventory_data["lead_time_days"]
        > FORECAST_HORIZON_DAYS
    ).any():
        raise InventoryInputError(
            "Lead time cannot exceed the 28-day forecast horizon."
        )

    unknown_products = inventory_data.loc[
        ~inventory_data["StockCode"].isin(forecast_data["StockCode"]),
        "StockCode",
    ].tolist()

    if unknown_products:
        preview = unknown_products[:10]
        raise InventoryInputError(
            "Inventory contains products without forecasts. "
            f"Examples: {preview}"
        )

    result = inventory_data.merge(
        forecast_data,
        on="StockCode",
        how="left",
        validate="one_to_one",
    )

    # Approximate daily demand from the four-week total.
    result["average_daily_demand"] = (
        result["forecast_4week_demand"] / FORECAST_HORIZON_DAYS
    )

    result["estimated_lead_time_demand"] = (
        result["average_daily_demand"] * result["lead_time_days"]
    )

    result["reorder_point"] = (
        result["estimated_lead_time_demand"]
        + result["safety_stock"]
    )

    # Stock level needed to cover the full forecast horizon plus buffer.
    result["target_stock_level"] = (
        result["forecast_4week_demand"]
        + result["safety_stock"]
    )

    result["estimated_days_of_cover"] = np.where(
        result["average_daily_demand"] > 0,
        result["current_stock"] / result["average_daily_demand"],
        np.nan,
    )

    result["reorder_required"] = (
        result["current_stock"] <= result["reorder_point"]
    )

    result["risk_status"] = np.select(
        [
            result["reorder_required"],
            result["current_stock"] < result["target_stock_level"],
        ],
        [
            "REORDER_NOW",
            "WATCH",
        ],
        default="HEALTHY",
    )

    order_gap = (
        result["target_stock_level"] - result["current_stock"]
    ).clip(lower=0)

    result["recommended_order_qty"] = np.where(
        result["reorder_required"],
        np.ceil(order_gap),
        0,
    ).astype("int64")

    result["demand_estimation_method"] = (
        "Four-week demand evenly distributed over 28 days"
    )

    return result.sort_values(
        ["risk_status", "StockCode"]
    ).reset_index(drop=True)
