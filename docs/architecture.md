# Architecture

## System context

Stockout Radar has three deployed/runtime components and one offline forecasting workflow:

1. **Forecasting workflow:** Python/Pandas feature construction and the saved Scikit-learn model produce a four-week demand forecast for each eligible product. `scripts/refresh_forecasts.py` persists a new forecast run. It is intentionally run offline rather than from a serverless HTTP request.
2. **Database:** Neon PostgreSQL stores forecast-run metadata, product forecasts, operator inventory inputs, assessment runs and recommendation rows. SQLite is the local-development default.
3. **Backend:** FastAPI exposes versioned REST endpoints. SQLAlchemy handles database access. Every `/api/v1` route uses bearer-key authorization in production.
4. **Frontend:** Next.js App Router renders the operational dashboard. A server-side route proxy forwards API calls to FastAPI and attaches the backend bearer key. A Next.js proxy checks the shared administrator HTTP Basic credentials for production application routes.

## Request flow

```text
Browser
  | HTTPS + HTTP Basic credentials
  v
Vercel frontend project (root: frontend)
  | proxy.ts validates shared admin credentials
  | /api/backend/* server-side route adds Bearer API key
  v
Vercel backend project (root: src)
  | FastAPI require_api_key dependency
  v
SQLAlchemy session
  |
  v
Neon PostgreSQL
```

The API key and database URL remain server-side environment variables. The browser does not call Neon directly and should never receive the backend bearer key.

## Forecast batch flow

```text
Online Retail II source workbook
  -> cleaning and product/week aggregation
  -> weekly_panel.csv
  -> build_feature_table / latest_feature_rows
  -> models/stockout_radar_v1.joblib
  -> DemandForecastService
  -> scripts/refresh_forecasts.py
  -> forecast_runs + product_forecasts
```

The deployed API reads the active persisted forecast run. It does not load the raw workbook or perform full model inference for each page request.

## Inventory assessment flow

```text
Operator enters current_stock, lead_time_days, safety_stock
  -> PUT /api/v1/inventory/{stock_code}
  -> inventory_items
  -> POST /api/v1/inventory/assessment
  -> active forecasts joined to all tracked inventory
  -> inventory_recommendations + assessment_runs
  -> GET /api/v1/inventory/assessment
  -> dashboard
```

An assessment snapshots calculated values. Updating inventory does not retroactively rewrite an older assessment; run a new assessment to create a new snapshot.

## Main code locations

| Path | Responsibility |
|---|---|
| `src/stockout_radar/features.py` | Weekly panel validation and feature generation |
| `src/stockout_radar/schema.py` | Canonical 16-feature model schema and target name |
| `src/stockout_radar/forecasting.py` | Four-week forecast service and non-negative clipping |
| `src/stockout_radar/model.py` | Saved model loading and prediction interface |
| `src/stockout_radar/inventory.py` | Reorder-point, target-stock and risk calculations |
| `src/stockout_radar/api/router.py` | Versioned API endpoints |
| `src/stockout_radar/api/security.py` | Backend bearer-key verification |
| `src/stockout_radar/api/database.py` | SQLite/PostgreSQL engine and session configuration |
| `src/stockout_radar/api/services.py` | Forecast persistence and assessment construction |
| `frontend/proxy.ts` | Production administrator Basic Authentication |
| `frontend/app/api/backend/[...path]/route.ts` | Server-side frontend-to-backend proxy |
| `scripts/refresh_forecasts.py` | Offline forecast generation and persistence |
| `scripts/migrate_sqlite_to_postgres.py` | One-time database migration utility |

## Deployment topology

| Component | Provider/project | Repository root | Region |
|---|---|---|---|
| Frontend | Vercel `stockout-radar` | `frontend` | `sin1` |
| Backend | Vercel `stockout-radar-api` | `src` | `sin1` |
| Database | Neon PostgreSQL | Managed service | Configured in Neon |

Each Vercel project is connected to the same GitHub repository and deploys from `main`. The project-specific `vercel.json` files set the Singapore function region.

## Current architectural boundaries

- One shared inventory namespace; no tenant isolation.
- One shared administrator login; no per-user identities or roles.
- Bearer API key is shared between the Next.js server-side proxy and FastAPI.
- Database schema initialization currently uses SQLAlchemy `create_all`; versioned Alembic migrations are not present.
- Forecast generation is an offline operation; scheduling and sales ingestion are not automated in this release.
- The application stores a single active forecast run and reads persisted assessments.
