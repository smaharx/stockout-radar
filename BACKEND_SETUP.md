# Stockout Radar — FastAPI backend milestone

This add-on creates the first API layer around the existing forecasting and inventory modules. It does not replace the ML pipeline or the inventory rules.

## 1. Copy files into the project

Extract this archive into the **root** of your existing `stockout-radar` repository and allow the folders to merge. It adds:

- `src/stockout_radar/api/` — FastAPI application, SQLAlchemy tables, schemas, routes, and persistence services.
- `scripts/refresh_forecasts.py` — runs the existing four-week forecasting service and stores the results in the configured database.
- `requirements-backend.txt` — API/database dependencies plus pinned ML dependencies.
- `.env.example` — local environment variable example.

Do not delete or replace your existing `src/stockout_radar/` files.

## 2. Install backend dependencies

From the project root, with your existing `.venv` activated:

```bash
pip install -r requirements-backend.txt
```

The project uses scikit-learn `1.8.0` because the saved model was produced with that version. Do not upgrade it independently.

## 3. Start the API locally

SQLite is the default, so a payment card, hosting account, or PostgreSQL server is not needed for local development.

```bash
uvicorn stockout_radar.api.main:app --reload --app-dir src
```

Open these local addresses in your browser:

- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/v1/health`

The first startup creates `stockout_radar.db` in the current working directory.

## 4. Load forecast data

The API reads forecast records from its database. Generate them using the project's existing saved model and weekly panel:

```bash
PYTHONPATH=src python scripts/refresh_forecasts.py
```

This requires the existing local files:

- `models/stockout_radar_v1.joblib`
- `data/processed/weekly_panel.csv`

Do not run the refresh script against a hosted database until you have configured and verified its `DATABASE_URL`. The generated Online Retail II forecasts are historical demonstration forecasts, not live 2026 demand forecasts.

## 5. API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | API and database health |
| GET | `/api/v1/products` | Search and page through forecasted products |
| GET | `/api/v1/forecasts` | Retrieve active four-week forecasts |
| GET | `/api/v1/inventory` | List saved inventory inputs |
| PUT | `/api/v1/inventory/{stock_code}` | Create or update inventory for a product |
| POST | `/api/v1/inventory/assessment` | Assess all saved inventory against the active forecasts |
| GET | `/api/v1/inventory/assessment` | Retrieve the most recent saved assessment |

Example inventory request for a valid forecasted product:

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/inventory/85123A \
  -H 'Content-Type: application/json' \
  -d '{"current_stock": 80, "lead_time_days": 7, "safety_stock": 20}'
```

Then run an assessment:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/inventory/assessment
```

Replace `85123A` with a product code returned by `/api/v1/products`; the example is illustrative, not guaranteed to exist in the prepared dataset.

## 6. Switch to PostgreSQL later

For local PostgreSQL or a hosted PostgreSQL provider, set `DATABASE_URL` in a root-level `.env` file. The code accepts `postgres://`, `postgresql://`, and `postgresql+psycopg://` URLs and uses the psycopg v3 driver.

Keep `.env` out of Git. Never paste database credentials into source code or commit them.

## 7. Important current-stage limitations

- This is the first backend milestone, not production-ready authentication or multi-user tenancy.
- Inventory is currently a single shared inventory list; user accounts and tenant isolation are a later security milestone.
- Database tables are initialized with SQLAlchemy `create_all` for the prototype. Add Alembic migrations before production schema changes.
- Forecast generation is intentionally an offline script, not a public API endpoint. This keeps expensive model inference out of serverless web requests and means the deployed API only needs to read the saved forecasts and execute inventory assessments.
- The existing inventory rule spreads four-week demand evenly across 28 days and limits lead time to 28 days. Its assumptions are exposed in the API response; they are not silently changed here.
- Before exposing a public deployment, add authentication, rate limiting, stricter CORS configuration, backups, and operational monitoring.
