# Backend setup guide

This file is retained as a short entry point for existing project references. The maintained documentation is in [`docs/deployment.md`](docs/deployment.md), [`docs/api-reference.md`](docs/api-reference.md), and [`docs/operations-runbook.md`](docs/operations-runbook.md).

## Local backend

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-backend.txt -r requirements-dev.txt
APP_ENV=local python -m uvicorn stockout_radar.api.main:app \
  --reload --app-dir src --port 8001
```

Interactive API documentation: <http://127.0.0.1:8001/docs>.

## Forecast persistence

A forecast refresh requires `models/stockout_radar_v1.joblib` and `data/processed/weekly_panel.csv`:

```bash
PYTHONPATH=src python scripts/refresh_forecasts.py
```

Forecast refresh is an offline/batch operation. Do not execute it against the production database unless an intentional new forecast run has been reviewed and the database is backed up.

## Production

The FastAPI Vercel project uses repository root directory `src`, entrypoint `src/main.py`, and `src/requirements.txt`. Its Production variables are `APP_ENV=production`, pooled Neon `DATABASE_URL`, and `STOCKOUT_RADAR_API_KEY`. The backend API requires a bearer token in production. Never commit the values.

For the detailed two-project Vercel and Neon configuration, see [`docs/deployment.md`](docs/deployment.md).
