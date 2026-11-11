import pytest

from stockout_radar.api.database import get_database_url


def test_local_environment_defaults_to_sqlite(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert get_database_url() == "sqlite:///./stockout_radar.db"


def test_production_requires_database_url(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        get_database_url()


def test_production_rejects_sqlite(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./stockout_radar.db")

    with pytest.raises(RuntimeError, match="SQLite"):
        get_database_url()


def test_postgresql_url_uses_psycopg_driver(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test_user:test_password@db.example.com/stockout_radar",
    )

    result = get_database_url()

    assert result.startswith("postgresql+psycopg://")
