"""FastAPI entry point for Stockout Radar."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stockout_radar.api.database import Base, make_engine, make_session_factory
from stockout_radar.api import db_models as _db_models  # register SQLAlchemy tables
from stockout_radar.api.router import router


def create_app(database_url: str | None = None) -> FastAPI:
    engine = make_engine(database_url)
    session_factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Bootstrap local development databases only.
        # Production schema is initialized through the migration process.
        app_env = os.getenv("APP_ENV", "local").strip().lower()
        if app_env not in {"production", "prod"}:
            Base.metadata.create_all(bind=engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="Stockout Radar API",
        description=(
            "Demand forecast and inventory decision-support API. Forecast demand "
            "is based on historical Online Retail II data; inventory inputs are "
            "provided by the operator."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory

    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(router)
    return app


app = create_app()
