"""SQLAlchemy tables used by the Stockout Radar API."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockout_radar.api.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_artifact: Mapped[str] = mapped_column(String(255), nullable=False)
    history_through_week: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_start_week: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    product_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    forecasts: Mapped[list["ProductForecast"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    assessments: Mapped[list["AssessmentRun"]] = relationship(back_populates="forecast_run")


class ProductForecast(Base):
    __tablename__ = "product_forecasts"
    __table_args__ = (UniqueConstraint("forecast_run_id", "stock_code", name="uq_forecast_run_product"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_run_id: Mapped[int] = mapped_column(ForeignKey("forecast_runs.id", ondelete="CASCADE"), index=True)
    stock_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    history_through_week: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_start_week: Mapped[date] = mapped_column(Date, nullable=False)
    raw_model_prediction: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_4week_demand: Mapped[float] = mapped_column(Float, nullable=False)
    prediction_was_clipped: Mapped[bool] = mapped_column(Boolean, nullable=False)
    forecast_horizon_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    run: Mapped[ForecastRun] = relationship(back_populates="forecasts")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    stock_code: Mapped[str] = mapped_column(String(100), primary_key=True)
    current_stock: Mapped[float] = mapped_column(Float, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_stock: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class AssessmentRun(Base):
    __tablename__ = "assessment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_run_id: Mapped[int] = mapped_column(ForeignKey("forecast_runs.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_now_count: Mapped[int] = mapped_column(Integer, nullable=False)
    watch_count: Mapped[int] = mapped_column(Integer, nullable=False)
    healthy_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_recommended_order_qty: Mapped[int] = mapped_column(Integer, nullable=False)

    forecast_run: Mapped[ForecastRun] = relationship(back_populates="assessments")
    recommendations: Mapped[list["InventoryRecommendation"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class InventoryRecommendation(Base):
    __tablename__ = "inventory_recommendations"
    __table_args__ = (UniqueConstraint("assessment_run_id", "stock_code", name="uq_assessment_product"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_run_id: Mapped[int] = mapped_column(ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True)
    stock_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    current_stock: Mapped[float] = mapped_column(Float, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_stock: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_4week_demand: Mapped[float] = mapped_column(Float, nullable=False)
    average_daily_demand: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_lead_time_demand: Mapped[float] = mapped_column(Float, nullable=False)
    reorder_point: Mapped[float] = mapped_column(Float, nullable=False)
    target_stock_level: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_days_of_cover: Mapped[float | None] = mapped_column(Float, nullable=True)
    reorder_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    risk_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    recommended_order_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    demand_estimation_method: Mapped[str] = mapped_column(String(255), nullable=False)

    assessment: Mapped[AssessmentRun] = relationship(back_populates="recommendations")
