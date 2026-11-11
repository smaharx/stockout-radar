"""Database configuration and session management."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


class Base(DeclarativeBase):
    """Base class for SQLAlchemy tables."""


def get_database_url() -> str:
    """Return DATABASE_URL, defaulting to a local SQLite database."""
    app_env = os.getenv("APP_ENV", "local").strip().lower()
    production = app_env in {"production", "prod"}

    configured_url = os.getenv("DATABASE_URL")

    if configured_url is None:
        if production:
            raise RuntimeError(
                "DATABASE_URL must be configured in production."
            )
        url = "sqlite:///./stockout_radar.db"
    else:
        url = configured_url.strip()

    if not url:
        raise ValueError("DATABASE_URL is set but empty.")

    if production and url.startswith("sqlite"):
        raise RuntimeError(
            "SQLite is not permitted in production. "
            "Configure the PostgreSQL database URL."
        )

    # Neon commonly supplies postgres:// or postgresql:// URLs. Use psycopg v3.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgres://")
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def make_engine(database_url: str | None = None) -> Engine:
    """Build an engine for SQLite or PostgreSQL."""
    url = database_url or get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

    # Serverless instances should not retain their own connection pools.
    # Use a pooled PostgreSQL URL supplied by the database provider.
    if (
        os.getenv("APP_ENV", "").lower() in {"production", "prod"}
        and not url.startswith("sqlite")
    ):
        return create_engine(
            url,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
            poolclass=NullPool,
        )

    return create_engine(
        url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    """FastAPI dependency that yields one request-scoped database session."""
    session_factory = request.app.state.session_factory
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
