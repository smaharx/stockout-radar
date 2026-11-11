from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from stockout_radar.api.security import require_api_key


def make_request(authorization: str | None = None):
    headers = {}
    if authorization is not None:
        headers["authorization"] = authorization
    return SimpleNamespace(headers=headers)


def test_local_development_allows_requests_without_api_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("STOCKOUT_RADAR_API_KEY", raising=False)

    require_api_key(make_request())


def test_production_fails_closed_when_api_key_is_missing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("STOCKOUT_RADAR_API_KEY", raising=False)

    with pytest.raises(HTTPException) as error:
        require_api_key(make_request())

    assert error.value.status_code == 503


def test_configured_api_key_rejects_missing_or_invalid_token(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("STOCKOUT_RADAR_API_KEY", "test-secret-token")

    with pytest.raises(HTTPException) as error:
        require_api_key(make_request("Bearer wrong-token"))

    assert error.value.status_code == 401


def test_configured_api_key_accepts_valid_token(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("STOCKOUT_RADAR_API_KEY", "test-secret-token")

    require_api_key(make_request("Bearer test-secret-token"))
