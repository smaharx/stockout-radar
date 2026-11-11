"""Vercel entrypoint for the Stockout Radar FastAPI service."""

from stockout_radar.api.main import app

__all__ = ["app"]
