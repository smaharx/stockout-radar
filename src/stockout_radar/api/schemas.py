"""Pydantic request and response schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    database: str


class InventoryItemWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    current_stock: float = Field(ge=0)
    lead_time_days: int = Field(ge=1, le=28)
    safety_stock: float = Field(ge=0)


class InventoryItemResponse(InventoryItemWrite):
    stock_code: str
    updated_at: datetime


class ForecastResponse(BaseModel):
    stock_code: str
    history_through_week: date
    forecast_start_week: date
    raw_model_prediction: float
    forecast_4week_demand: float
    prediction_was_clipped: bool
    forecast_horizon_weeks: int
    model_artifact: str


class ForecastListResponse(BaseModel):
    items: list[ForecastResponse]
    total: int
    forecast_run_id: int


class ProductResponse(BaseModel):
    stock_code: str
    forecast_4week_demand: float
    forecast_start_week: date


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int


class AssessmentSummary(BaseModel):
    assessment_run_id: int
    forecast_run_id: int
    created_at: datetime
    item_count: int
    reorder_now_count: int
    watch_count: int
    healthy_count: int
    total_recommended_order_qty: int


class RecommendationResponse(BaseModel):
    stock_code: str
    current_stock: float
    lead_time_days: int
    safety_stock: float
    forecast_4week_demand: float
    average_daily_demand: float
    estimated_lead_time_demand: float
    reorder_point: float
    target_stock_level: float
    estimated_days_of_cover: float | None
    reorder_required: bool
    risk_status: str
    recommended_order_qty: int
    demand_estimation_method: str


class AssessmentResponse(BaseModel):
    summary: AssessmentSummary
    recommendations: list[RecommendationResponse]
