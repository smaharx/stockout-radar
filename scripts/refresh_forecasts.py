#!/usr/bin/env python3
"""Generate forecasts locally and load the active forecast run into DATABASE_URL."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from stockout_radar.api.database import Base, make_engine, make_session_factory  # noqa: E402
from stockout_radar.api import db_models as _db_models  # noqa: E402,F401
from stockout_radar.api.services import persist_forecasts  # noqa: E402
from stockout_radar.forecasting import DemandForecastService  # noqa: E402


def main() -> None:
    engine = make_engine()
    Base.metadata.create_all(bind=engine)
    SessionLocal = make_session_factory(engine)

    try:
        print("Generating four-week forecasts using the saved Stockout Radar model...")
        forecast_frame = DemandForecastService().forecast_from_file()
        print(f"Generated forecasts for {len(forecast_frame):,} products.")
        with SessionLocal() as session:
            run = persist_forecasts(session, forecast_frame)
        print(f"Saved forecast run #{run.id}; {run.product_count:,} products; model={run.model_artifact}.")
        print("This forecast run is now active in the configured database.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
