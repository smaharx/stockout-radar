"""Versioned HTTP endpoints for Stockout Radar."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from stockout_radar.api.database import get_db
from stockout_radar.api.security import require_api_key
from stockout_radar.api.db_models import (
    AssessmentRun,
    ForecastRun,
    InventoryItem,
    InventoryRecommendation,
    ProductForecast,
)
from stockout_radar.api.schemas import (
    AssessmentResponse,
    AssessmentSummary,
    ForecastListResponse,
    ForecastResponse,
    HealthResponse,
    InventoryItemResponse,
    InventoryItemWrite,
    ProductListResponse,
    ProductResponse,
    RecommendationResponse,
)
from stockout_radar.api.services import (
    ForecastDataUnavailable,
    build_assessment,
    get_active_forecast_run,
)


router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_api_key)],
)


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(request: Request):
    """Return application and database health."""
    try:
        with request.app.state.engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    except Exception as exc:  # database readiness is part of this endpoint
        raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
    return HealthResponse(status="ok", database="connected")


@router.get("/products", response_model=ProductListResponse, tags=["products"])
def list_products(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    try:
        run = get_active_forecast_run(db)
    except ForecastDataUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    query = select(ProductForecast).where(ProductForecast.forecast_run_id == run.id)
    count_query = select(func.count()).select_from(ProductForecast).where(
        ProductForecast.forecast_run_id == run.id
    )
    if search:
        query = query.where(ProductForecast.stock_code.ilike(f"%{search.strip()}%"))
        count_query = count_query.where(ProductForecast.stock_code.ilike(f"%{search.strip()}%"))
    rows = db.scalars(query.order_by(ProductForecast.stock_code).limit(limit).offset(offset)).all()
    total = int(db.scalar(count_query) or 0)
    return ProductListResponse(
        items=[
            ProductResponse(
                stock_code=row.stock_code,
                forecast_4week_demand=row.forecast_4week_demand,
                forecast_start_week=row.forecast_start_week,
            )
            for row in rows
        ],
        total=total,
    )


@router.get("/forecasts", response_model=ForecastListResponse, tags=["forecasts"])
def list_forecasts(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    try:
        run = get_active_forecast_run(db)
    except ForecastDataUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    query = select(ProductForecast).where(ProductForecast.forecast_run_id == run.id)
    count_query = select(func.count()).select_from(ProductForecast).where(
        ProductForecast.forecast_run_id == run.id
    )
    if search:
        query = query.where(ProductForecast.stock_code.ilike(f"%{search.strip()}%"))
        count_query = count_query.where(ProductForecast.stock_code.ilike(f"%{search.strip()}%"))
    rows = db.scalars(query.order_by(ProductForecast.stock_code).limit(limit).offset(offset)).all()
    total = int(db.scalar(count_query) or 0)
    return ForecastListResponse(
        items=[
            ForecastResponse(
                stock_code=row.stock_code,
                history_through_week=row.history_through_week,
                forecast_start_week=row.forecast_start_week,
                raw_model_prediction=row.raw_model_prediction,
                forecast_4week_demand=row.forecast_4week_demand,
                prediction_was_clipped=row.prediction_was_clipped,
                forecast_horizon_weeks=row.forecast_horizon_weeks,
                model_artifact=run.model_artifact,
            )
            for row in rows
        ],
        total=total,
        forecast_run_id=run.id,
    )


@router.get("/inventory", response_model=list[InventoryItemResponse], tags=["inventory"])
def list_inventory(db: Session = Depends(get_db)):
    rows = db.scalars(select(InventoryItem).order_by(InventoryItem.stock_code)).all()
    return [
        InventoryItemResponse(
            stock_code=row.stock_code,
            current_stock=row.current_stock,
            lead_time_days=row.lead_time_days,
            safety_stock=row.safety_stock,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.put(
    "/inventory/{stock_code}",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_200_OK,
    tags=["inventory"],
)
def upsert_inventory(
    stock_code: str,
    payload: InventoryItemWrite,
    db: Session = Depends(get_db),
):
    code = stock_code.strip()
    if not code or len(code) > 100:
        raise HTTPException(status_code=422, detail="StockCode must be 1-100 characters.")

    try:
        run = get_active_forecast_run(db)
    except ForecastDataUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    known_product = db.scalar(
        select(ProductForecast.id).where(
            ProductForecast.forecast_run_id == run.id,
            ProductForecast.stock_code == code,
        )
    )
    if known_product is None:
        raise HTTPException(status_code=404, detail=f"Product '{code}' has no active forecast.")

    item = db.get(InventoryItem, code)
    if item is None:
        item = InventoryItem(stock_code=code, **payload.model_dump())
        db.add(item)
    else:
        item.current_stock = payload.current_stock
        item.lead_time_days = payload.lead_time_days
        item.safety_stock = payload.safety_stock
    db.commit()
    db.refresh(item)
    return InventoryItemResponse(
        stock_code=item.stock_code,
        current_stock=item.current_stock,
        lead_time_days=item.lead_time_days,
        safety_stock=item.safety_stock,
        updated_at=item.updated_at,
    )


@router.post("/inventory/assessment", response_model=AssessmentResponse, tags=["inventory"])
def run_inventory_assessment(db: Session = Depends(get_db)):
    try:
        forecast_run = get_active_forecast_run(db)
    except ForecastDataUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    inventory_items = db.scalars(select(InventoryItem).order_by(InventoryItem.stock_code)).all()
    try:
        assessment, result = build_assessment(db, forecast_run, inventory_items)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AssessmentResponse(
        summary=AssessmentSummary(
            assessment_run_id=assessment.id,
            forecast_run_id=assessment.forecast_run_id,
            created_at=assessment.created_at,
            item_count=assessment.item_count,
            reorder_now_count=assessment.reorder_now_count,
            watch_count=assessment.watch_count,
            healthy_count=assessment.healthy_count,
            total_recommended_order_qty=assessment.total_recommended_order_qty,
        ),
        recommendations=[
            RecommendationResponse(
                stock_code=str(row["StockCode"]),
                current_stock=float(row["current_stock"]),
                lead_time_days=int(row["lead_time_days"]),
                safety_stock=float(row["safety_stock"]),
                forecast_4week_demand=float(row["forecast_4week_demand"]),
                average_daily_demand=float(row["average_daily_demand"]),
                estimated_lead_time_demand=float(row["estimated_lead_time_demand"]),
                reorder_point=float(row["reorder_point"]),
                target_stock_level=float(row["target_stock_level"]),
                estimated_days_of_cover=None
                if row["estimated_days_of_cover"] != row["estimated_days_of_cover"]
                else float(row["estimated_days_of_cover"]),
                reorder_required=bool(row["reorder_required"]),
                risk_status=str(row["risk_status"]),
                recommended_order_qty=int(row["recommended_order_qty"]),
                demand_estimation_method=str(row["demand_estimation_method"]),
            )
            for row in result.to_dict(orient="records")
        ],
    )


@router.get("/inventory/assessment", response_model=AssessmentResponse, tags=["inventory"])
def get_latest_assessment(db: Session = Depends(get_db)):
    assessment = db.scalar(select(AssessmentRun).order_by(AssessmentRun.created_at.desc(), AssessmentRun.id.desc()))
    if assessment is None:
        raise HTTPException(status_code=404, detail="No inventory assessment has been run yet.")
    rows = db.scalars(
        select(InventoryRecommendation)
        .where(InventoryRecommendation.assessment_run_id == assessment.id)
        .order_by(InventoryRecommendation.stock_code)
    ).all()
    return AssessmentResponse(
        summary=AssessmentSummary(
            assessment_run_id=assessment.id,
            forecast_run_id=assessment.forecast_run_id,
            created_at=assessment.created_at,
            item_count=assessment.item_count,
            reorder_now_count=assessment.reorder_now_count,
            watch_count=assessment.watch_count,
            healthy_count=assessment.healthy_count,
            total_recommended_order_qty=assessment.total_recommended_order_qty,
        ),
        recommendations=[
            RecommendationResponse(
                stock_code=row.stock_code,
                current_stock=row.current_stock,
                lead_time_days=row.lead_time_days,
                safety_stock=row.safety_stock,
                forecast_4week_demand=row.forecast_4week_demand,
                average_daily_demand=row.average_daily_demand,
                estimated_lead_time_demand=row.estimated_lead_time_demand,
                reorder_point=row.reorder_point,
                target_stock_level=row.target_stock_level,
                estimated_days_of_cover=row.estimated_days_of_cover,
                reorder_required=row.reorder_required,
                risk_status=row.risk_status,
                recommended_order_qty=row.recommended_order_qty,
                demand_estimation_method=row.demand_estimation_method,
            )
            for row in rows
        ],
    )
