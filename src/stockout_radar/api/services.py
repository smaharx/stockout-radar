"""Persistence and application services for forecasts and assessments."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from stockout_radar.api.db_models import (
    AssessmentRun,
    ForecastRun,
    InventoryItem,
    InventoryRecommendation,
    ProductForecast,
)


class ForecastDataUnavailable(RuntimeError):
    """Raised when no forecast run is available for the API to use."""


def persist_forecasts(session: Session, forecasts: pd.DataFrame) -> ForecastRun:
    """Save a complete forecast frame and make its run active."""
    required = {
        "StockCode",
        "history_through_week",
        "forecast_start_week",
        "raw_model_prediction",
        "forecast_4week_demand",
        "prediction_was_clipped",
        "forecast_horizon_weeks",
        "model_artifact",
    }
    missing = sorted(required.difference(forecasts.columns))
    if missing:
        raise ValueError(f"Forecast frame is missing required columns: {missing}")
    if forecasts.empty:
        raise ValueError("Cannot save an empty forecast run.")
    if forecasts["StockCode"].isna().any() or forecasts["StockCode"].duplicated().any():
        raise ValueError("Forecast frame must have unique, non-empty StockCode values.")

    model_artifacts = forecasts["model_artifact"].dropna().astype(str).unique()
    if len(model_artifacts) != 1:
        raise ValueError("A forecast run must use exactly one model artifact.")
    if not (pd.to_numeric(forecasts["forecast_horizon_weeks"], errors="coerce") == 4).all():
        raise ValueError("Only four-week forecasts can be saved.")

    history_week = pd.to_datetime(forecasts["history_through_week"]).max().date()
    forecast_week = pd.to_datetime(forecasts["forecast_start_week"]).min().date()

    session.query(ForecastRun).filter(ForecastRun.is_active.is_(True)).update(
        {ForecastRun.is_active: False}, synchronize_session=False
    )
    run = ForecastRun(
        model_artifact=model_artifacts[0],
        history_through_week=history_week,
        forecast_start_week=forecast_week,
        horizon_weeks=4,
        product_count=len(forecasts),
        is_active=True,
    )
    session.add(run)
    session.flush()

    rows = []
    for row in forecasts.to_dict(orient="records"):
        rows.append(
            ProductForecast(
                forecast_run_id=run.id,
                stock_code=str(row["StockCode"]),
                history_through_week=pd.Timestamp(row["history_through_week"]).date(),
                forecast_start_week=pd.Timestamp(row["forecast_start_week"]).date(),
                raw_model_prediction=float(row["raw_model_prediction"]),
                forecast_4week_demand=float(row["forecast_4week_demand"]),
                prediction_was_clipped=bool(row["prediction_was_clipped"]),
                forecast_horizon_weeks=int(row["forecast_horizon_weeks"]),
            )
        )
    session.add_all(rows)
    session.commit()
    session.refresh(run)
    return run


def get_active_forecast_run(session: Session) -> ForecastRun:
    run = session.scalar(
        select(ForecastRun).where(ForecastRun.is_active.is_(True)).order_by(ForecastRun.created_at.desc())
    )
    if run is None:
        raise ForecastDataUnavailable(
            "No forecast data is loaded. Generate and load forecasts with "
            "python scripts/refresh_forecasts.py."
        )
    return run


def build_assessment(session: Session, forecast_run: ForecastRun, inventory_items: list[InventoryItem]):
    """Run the existing inventory engine and save the recommendation snapshot."""
    if not inventory_items:
        raise ValueError("No inventory has been entered. Add at least one inventory item first.")

    # Import here so the forecast read API doesn't eagerly import the ML stack.
    from stockout_radar.inventory import assess_inventory

    forecast_rows = session.scalars(
        select(ProductForecast).where(ProductForecast.forecast_run_id == forecast_run.id)
    ).all()
    forecast_frame = pd.DataFrame(
        [
            {
                "StockCode": item.stock_code,
                "forecast_4week_demand": item.forecast_4week_demand,
                "forecast_horizon_weeks": item.forecast_horizon_weeks,
            }
            for item in forecast_rows
        ]
    )
    inventory_frame = pd.DataFrame(
        [
            {
                "StockCode": item.stock_code,
                "current_stock": item.current_stock,
                "lead_time_days": item.lead_time_days,
                "safety_stock": item.safety_stock,
            }
            for item in inventory_items
        ]
    )

    result = assess_inventory(forecast_frame, inventory_frame)
    statuses = result["risk_status"].value_counts().to_dict()
    total_order_qty = int(result["recommended_order_qty"].sum())

    assessment = AssessmentRun(
        forecast_run_id=forecast_run.id,
        item_count=len(result),
        reorder_now_count=int(statuses.get("REORDER_NOW", 0)),
        watch_count=int(statuses.get("WATCH", 0)),
        healthy_count=int(statuses.get("HEALTHY", 0)),
        total_recommended_order_qty=total_order_qty,
    )
    session.add(assessment)
    session.flush()

    saved_recommendations = []
    for row in result.to_dict(orient="records"):
        cover = row["estimated_days_of_cover"]
        saved_recommendations.append(
            InventoryRecommendation(
                assessment_run_id=assessment.id,
                stock_code=str(row["StockCode"]),
                current_stock=float(row["current_stock"]),
                lead_time_days=int(row["lead_time_days"]),
                safety_stock=float(row["safety_stock"]),
                forecast_4week_demand=float(row["forecast_4week_demand"]),
                average_daily_demand=float(row["average_daily_demand"]),
                estimated_lead_time_demand=float(row["estimated_lead_time_demand"]),
                reorder_point=float(row["reorder_point"]),
                target_stock_level=float(row["target_stock_level"]),
                estimated_days_of_cover=None if pd.isna(cover) else float(cover),
                reorder_required=bool(row["reorder_required"]),
                risk_status=str(row["risk_status"]),
                recommended_order_qty=int(row["recommended_order_qty"]),
                demand_estimation_method=str(row["demand_estimation_method"]),
            )
        )
    session.add_all(saved_recommendations)
    session.commit()
    session.refresh(assessment)
    return assessment, result
