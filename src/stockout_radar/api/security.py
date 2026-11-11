"""API-key authorization for Stockout Radar endpoints."""

from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request


def require_api_key(request: Request) -> None:
    """Require a bearer token when configured; fail closed in production."""

    expected = os.getenv("STOCKOUT_RADAR_API_KEY")

    if not expected:
        environment = os.getenv("APP_ENV", "local").lower()

        if environment in {"production", "prod"}:
            raise HTTPException(
                status_code=503,
                detail="API authentication is not configured.",
            )

        # Local development remains usable without deployment secrets.
        return

    authorization = request.headers.get("authorization", "")
    scheme, separator, supplied = authorization.partition(" ")

    valid = (
        separator == " "
        and scheme.lower() == "bearer"
        and bool(supplied)
        and hmac.compare_digest(
            supplied.encode("utf-8"),
            expected.encode("utf-8"),
        )
    )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="A valid API bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
