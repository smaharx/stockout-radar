from datetime import date

from fastapi.testclient import TestClient

from stockout_radar.api.db_models import ForecastRun, ProductForecast
from stockout_radar.api.main import create_app


def make_client(tmp_path, *, seed_forecasts=True):
    database_path = tmp_path / "api-test.db"
    app = create_app(f"sqlite:///{database_path}")
    client = TestClient(app)
    client.__enter__()

    if seed_forecasts:
        with app.state.session_factory() as session:
            run = ForecastRun(
                model_artifact="stockout_radar_v1.joblib",
                history_through_week=date(2011, 11, 28),
                forecast_start_week=date(2011, 12, 5),
                horizon_weeks=4,
                product_count=2,
                is_active=True,
            )
            session.add(run)
            session.flush()
            session.add_all(
                [
                    ProductForecast(
                        forecast_run_id=run.id,
                        stock_code="SKU-001",
                        history_through_week=date(2011, 11, 28),
                        forecast_start_week=date(2011, 12, 5),
                        raw_model_prediction=280.0,
                        forecast_4week_demand=280.0,
                        prediction_was_clipped=False,
                        forecast_horizon_weeks=4,
                    ),
                    ProductForecast(
                        forecast_run_id=run.id,
                        stock_code="SKU-002",
                        history_through_week=date(2011, 11, 28),
                        forecast_start_week=date(2011, 12, 5),
                        raw_model_prediction=40.0,
                        forecast_4week_demand=40.0,
                        prediction_was_clipped=False,
                        forecast_horizon_weeks=4,
                    ),
                ]
            )
            session.commit()
    return client


def test_health_and_product_forecast_routes(tmp_path):
    client = make_client(tmp_path)
    try:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok", "database": "connected"}

        products = client.get("/api/v1/products?search=SKU-001")
        assert products.status_code == 200
        assert products.json()["total"] == 1
        assert products.json()["items"][0]["stock_code"] == "SKU-001"

        forecasts = client.get("/api/v1/forecasts")
        assert forecasts.status_code == 200
        assert forecasts.json()["total"] == 2
        assert forecasts.json()["items"][0]["forecast_horizon_weeks"] == 4
    finally:
        client.__exit__(None, None, None)


def test_inventory_upsert_and_assessment_routes(tmp_path):
    client = make_client(tmp_path)
    try:
        saved = client.put(
            "/api/v1/inventory/SKU-001",
            json={"current_stock": 50, "lead_time_days": 7, "safety_stock": 20},
        )
        assert saved.status_code == 200
        assert saved.json()["stock_code"] == "SKU-001"

        assessment = client.post("/api/v1/inventory/assessment")
        assert assessment.status_code == 200, assessment.text
        payload = assessment.json()
        assert payload["summary"]["item_count"] == 1
        assert payload["summary"]["reorder_now_count"] == 1
        recommendation = payload["recommendations"][0]
        assert recommendation["risk_status"] == "REORDER_NOW"
        assert recommendation["reorder_point"] == 90.0
        assert recommendation["recommended_order_qty"] == 250

        latest = client.get("/api/v1/inventory/assessment")
        assert latest.status_code == 200
        assert latest.json()["summary"]["assessment_run_id"] == payload["summary"]["assessment_run_id"]
    finally:
        client.__exit__(None, None, None)


def test_forecast_routes_explain_when_forecasts_not_loaded(tmp_path):
    client = make_client(tmp_path, seed_forecasts=False)
    try:
        response = client.get("/api/v1/forecasts")
        assert response.status_code == 409
        assert "refresh_forecasts.py" in response.json()["detail"]
    finally:
        client.__exit__(None, None, None)


def test_persist_forecasts_replaces_active_run(tmp_path):
    import pandas as pd
    from sqlalchemy import select

    from stockout_radar.api.db_models import ForecastRun, ProductForecast
    from stockout_radar.api.services import persist_forecasts

    client = make_client(tmp_path, seed_forecasts=False)
    try:
        frame = pd.DataFrame(
            [
                {
                    "StockCode": "SKU-NEW",
                    "history_through_week": "2011-11-28",
                    "forecast_start_week": "2011-12-05",
                    "raw_model_prediction": 12.5,
                    "forecast_4week_demand": 12.5,
                    "prediction_was_clipped": False,
                    "forecast_horizon_weeks": 4,
                    "model_artifact": "stockout_radar_v1.joblib",
                }
            ]
        )
        with client.app.state.session_factory() as session:
            first = persist_forecasts(session, frame)
            second = persist_forecasts(session, frame)
            active_runs = session.scalars(
                select(ForecastRun).where(ForecastRun.is_active.is_(True))
            ).all()
            assert len(active_runs) == 1
            assert active_runs[0].id == second.id
            stored_forecasts = session.scalars(
                select(ProductForecast).where(ProductForecast.forecast_run_id == second.id)
            ).all()
            assert len(stored_forecasts) == 1
            assert stored_forecasts[0].stock_code == "SKU-NEW"
            assert first.id != second.id
    finally:
        client.__exit__(None, None, None)
