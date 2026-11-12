# Stockout Radar

**Historical product-demand forecasting and inventory replenishment decision support for small retailers.**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162.2-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.4.6-black?logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.3.1-087ea4?logo=react)](https://react.dev/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20Neon-4169e1?logo=postgresql)](https://www.postgresql.org/)
[![Backend tests](https://img.shields.io/badge/Backend%20tests-40%20passing-brightgreen)](https://github.com/smaharx/stockout-radar/tree/main/tests)
[![CI](https://github.com/smaharx/stockout-radar/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/smaharx/stockout-radar/actions/workflows/ci.yml)
[![Dataset licence](https://img.shields.io/badge/Dataset%20licence-CC%20BY%204.0-lightgrey)](https://creativecommons.org/licenses/by/4.0/)
[![Software licence](https://img.shields.io/badge/Software%20licence-not%20declared-lightgrey)](docs/licensing.md)

> **Important scope statement:** Stockout Radar forecasts demand from historical sales and applies an inventory replenishment rule to operator-supplied stock inputs. The source dataset contains no historical stock balances or stockout labels. The project therefore does **not** directly predict or validate stockout events.

## Live deployments

- **Frontend:** [https://stockout-radar.vercel.app](https://stockout-radar.vercel.app)
- **Backend API:** [https://stockout-radar-api.vercel.app](https://stockout-radar-api.vercel.app)
- **API base path:** `/api/v1`

The production frontend uses a single shared administrator HTTP Basic Authentication gate. Backend API routes require a bearer API key. Do not publish credentials or place them in browser-visible `NEXT_PUBLIC_` variables.

## What the system does

1. Builds a product-by-week demand panel from Online Retail II transactions.
2. Engineers lagged, rolling, price, trend and calendar features using information available before the forecast week.
3. Uses a trained `HistGradientBoosting` model to estimate aggregate unit demand over the next four weeks for each eligible product.
4. Persists forecast runs and product forecasts in PostgreSQL.
5. Lets an operator maintain current stock, supplier lead time and safety stock.
6. Compares saved inventory inputs with forecasts and persists a replenishment assessment.
7. Presents the catalog, forecast records, inventory and recommendations in a Next.js dashboard.

## Production acceptance snapshot

The following was observed during the production workflow demonstration on **12 November 2026**. It is a point-in-time demonstration result, not a permanent count or a model-accuracy claim.

| Item | Observed result |
|---|---:|
| Latest assessment | #4 |
| Products assessed | 3 |
| Reorder now | 3 |
| Watch | 0 |
| Healthy | 0 |
| Suggested replenishment | 51 units |

The user interface also confirmed that an inventory update for product `21003` was saved. Production records can change as operators add or update inventory and run assessments.

## Architecture

```text
UCI Online Retail II (historical transactions)
                |
                v
       Cleaning and weekly panel
                |
                v
       16 leakage-controlled features
                |
                v
     HistGradientBoosting model artifact
                |
                v
    Offline forecast refresh script
                |
                v
        Neon PostgreSQL database
          |                 |
          |                 +---- Operator inventory inputs
          |                              |
          +-------------+----------------+
                        v
              Inventory assessment
                        |
                        v
             Persisted recommendations
                        |
                        v
                FastAPI REST API
                        ^
                        | bearer API key
                        |
              Next.js server-side proxy
                        ^
                        | administrator Basic Auth
                        |
                 Browser / user
```

**Deployment boundary:** model inference and forecast generation are an offline/batch operation. The serverless API reads persisted forecasts and runs inventory assessments; it does not train the model or regenerate all product forecasts on a public request.

See [Architecture](docs/architecture.md), [API reference](docs/api-reference.md), and [Deployment runbook](docs/deployment.md).

## Technology stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12; Node.js 24 for the frontend build |
| Data processing | Pandas 3.1.1, NumPy 2.5.4 |
| Machine learning | Scikit-learn 1.8.0; `HistGradientBoosting` |
| Model persistence | Joblib 1.6.0 |
| Backend | FastAPI 0.162.2, SQLAlchemy 2.1.8, Uvicorn |
| Database | PostgreSQL on Neon; SQLite for local development |
| Frontend | Next.js 16.4.6, React 19.3.1, TypeScript |
| UI icons | Lucide React 1.70.0 |
| Tests and checks | Pytest, TypeScript, ESLint, Next.js production build |
| Hosting | Two Vercel projects (frontend and backend) |

The saved model was created with Scikit-learn 1.8.0. Keep the pinned model/runtime versions in `requirements-backend.txt` compatible when loading or retraining the serialized artifact.

## Dataset and preparation

- **Dataset:** [Online Retail II — UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/502/online+retail)
- **Dataset licence:** [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
- **Transaction period:** 1 December 2009 to 9 December 2011.
- **Source size:** 1,067,371 transactions.
- Raw and processed transaction files are deliberately excluded from Git because of their size. Download the source data separately and follow the analysis notebooks before rebuilding the weekly panel.

The documented cleaned panel contains 4,675 products and 407,702 product-weeks. The training workflow filters rows that do not have the required lag/rolling history and a complete four-week future target. See [Model card](docs/model-card.md) for the full task definition, split and known limitations.

## Forecast definition and feature set

The prediction target is **total units sold over the current forecast origin week and the following three weeks** (four-week aggregate demand). It is not four separate weekly predictions.

The 16 model features are:

`units_lag1`, `units_lag2`, `units_lag4`, `units_mean4`, `units_std4`, `units_mean8`, `units_std8`, `orders_lag1`, `orders4`, `price_lag1`, `price_change4`, `trend_ratio`, `week_of_year`, `month`, `weeks_to_xmas`, and `product_age`.

Lagged and rolling sales/order/price features are shifted so that model inputs use information through the week before the prediction origin. The four-week target is used only as the label during training.

## Evaluation results

The committed retrospective holdout report records 48,511 product-week observations over the test origins 29 August–7 November 2011.

| Model | MAE (units) | RMSE (units) | WAPE |
|---|---:|---:|---:|
| Selected model (`HistGradientBoosting`) | 59.2246 | 236.0493 | 47.7349% |
| Four-week moving-average baseline | 66.1085 | 236.2272 | 53.2833% |

The selected model improves aggregate MAE by approximately 6.88 units and WAPE by approximately 5.55 percentage points versus the moving-average baseline. It has lower RMSE by a small margin. At product level, it has lower MAE than the baseline for 1,809 of 4,484 evaluated products (about 40.3%); therefore, aggregate improvement does not mean the model wins for most individual products. Bulk-order spikes and product-level variation remain important limitations.

Metric values are retrospective results on historical data; they are not current-market accuracy guarantees. See `reports/metrics/holdout_evaluation.json` and [Model card](docs/model-card.md).

## Inventory and replenishment logic

Operators provide three values per product:

- `current_stock`: verified on-hand units.
- `lead_time_days`: supplier replenishment lead time, from 1 to 28 days.
- `safety_stock`: buffer units held above estimated lead-time demand.

The current rule assumes the four-week demand forecast is distributed evenly over 28 days:

```text
average_daily_demand = forecast_4week_demand / 28
estimated_lead_time_demand = average_daily_demand * lead_time_days
reorder_point = estimated_lead_time_demand + safety_stock
target_stock_level = forecast_4week_demand + safety_stock
```

Risk classification:

- `REORDER_NOW` when `current_stock <= reorder_point`.
- `WATCH` when the reorder point is not breached but `current_stock < target_stock_level`.
- `HEALTHY` otherwise.

When reorder is required, recommended quantity is the ceiling of the positive gap between target stock and current stock; otherwise it is zero. This is a decision-support heuristic, not a purchase order. It does not currently account for open purchase orders, reservations, supplier minimums, multiple locations, variable daily seasonality, or uncertainty intervals.

## Local development

### Prerequisites

- Python 3.12
- Node.js 20.9 or newer (Node.js 24 is used in the current deployment configuration)
- npm and Git
- The model artifact `models/stockout_radar_v1.joblib`
- For regenerating forecasts: `data/processed/weekly_panel.csv`

### 1. Clone and create the Python environment

```bash
git clone https://github.com/smaharx/stockout-radar.git
cd stockout-radar
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-backend.txt
python -m pip install -r requirements-dev.txt
```

`requirements-backend.txt` pins the numerical/model versions used by the saved artifact. `requirements.txt` also includes dependencies used by the original analysis/notebooks.

### 3. Configure local environment

```bash
cp .env.example .env
```

Local development defaults to SQLite when `APP_ENV=local` and `DATABASE_URL` is unset. The local frontend uses `frontend/.env.local`:

```dotenv
STOCKOUT_RADAR_API_URL=http://127.0.0.1:8001
```

Do not put real secrets in tracked files. `.env`, `.env.local`, database files, virtual environments and build output are ignored by Git.

### 4. Prepare data and refresh forecasts (only when rebuilding the forecast snapshot)

The refresh job requires the prepared weekly panel and saved model artifact:

```bash
PYTHONPATH=src python scripts/refresh_forecasts.py
```

The raw/processed datasets are not included in the repository. Follow the analysis notebooks to download, clean and aggregate the UCI data and produce `data/processed/weekly_panel.csv` before running the refresh. Do not run this command against production unless you deliberately intend to replace the active forecast run and have backed up the database.

### 5. Start the backend

From the repository root, in terminal 1:

```bash
source .venv/bin/activate
APP_ENV=local python -m uvicorn stockout_radar.api.main:app \
  --reload --app-dir src --port 8001
```

- API base: `http://127.0.0.1:8001/api/v1`
- Swagger UI: `http://127.0.0.1:8001/docs`
- Health: `http://127.0.0.1:8001/api/v1/health`

### 6. Start the frontend

In terminal 2:

```bash
cd frontend
npm ci
```

Create `frontend/.env.local` with the backend URL shown above, then:

```bash
npm run dev
```

Open `http://localhost:3000`. The production-only administrator gate is bypassed in Next.js development mode; local API-key enforcement is also relaxed when local `APP_ENV` has no API key configured. Never copy production secrets into a public or shared development environment.

## API overview

All application routes use `/api/v1` and require a bearer token when `STOCKOUT_RADAR_API_KEY` is configured (required in production).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | API and database readiness |
| `GET` | `/api/v1/products` | Search/paginate catalog products with active forecasts |
| `GET` | `/api/v1/forecasts` | Search/paginate active four-week forecasts |
| `GET` | `/api/v1/inventory` | List operator inventory inputs |
| `PUT` | `/api/v1/inventory/{stock_code}` | Create or update one product's inventory inputs |
| `POST` | `/api/v1/inventory/assessment` | Calculate and persist an assessment for all tracked items |
| `GET` | `/api/v1/inventory/assessment` | Retrieve the latest saved assessment |

`products` and `forecasts` accept `search`, `limit` (1–200) and `offset` query parameters. See [API reference](docs/api-reference.md) for examples and payload fields.

## Testing and quality checks

Backend tests (the last user-run verification recorded 40 passing tests):

```bash
source .venv/bin/activate
APP_ENV=local PYTHONPATH=src python -m pytest -q
python -m pip check
```

Frontend checks:

```bash
cd frontend
npm ci
npm run typecheck
npm run lint
npm run build
```

The repository also includes a GitHub Actions workflow that runs backend tests and frontend checks on pushes and pull requests. Passing CI does not replace the production smoke tests documented in [Testing](docs/testing.md).

## Production deployment

The production installation consists of two Vercel projects connected to the same GitHub repository plus a Neon PostgreSQL database.

| Service | Vercel project | Root directory | Region | Production domain |
|---|---|---|---|---|
| Frontend | `stockout-radar` | `frontend` | `sin1` (Singapore) | `https://stockout-radar.vercel.app` |
| Backend | `stockout-radar-api` | `src` | `sin1` (Singapore) | `https://stockout-radar-api.vercel.app` |
| Database | Neon | Managed PostgreSQL | Provider region | Private connection string |

Backend Production variables:

- `APP_ENV=production`
- `DATABASE_URL`: Neon **pooled** PostgreSQL connection string for the serverless runtime.
- `STOCKOUT_RADAR_API_KEY`: private bearer token.

Frontend Production variables:

- `STOCKOUT_RADAR_API_URL=https://stockout-radar-api.vercel.app`
- `STOCKOUT_RADAR_API_KEY`: exactly the same bearer token configured in the backend.
- `STOCKOUT_RADAR_ADMIN_USER`: administrator username.
- `STOCKOUT_RADAR_ADMIN_PASSWORD`: strong administrator password.

The frontend proxy adds the bearer token server-side; it is not sent to browser JavaScript. The app's administrator gate uses HTTP Basic Authentication. Both are shared single-admin demonstration controls, not multi-user identity, tenant isolation or a role-based authorization system.

For the one-time SQLite-to-Neon migration, use the **direct** Neon connection string in the migration process. Use the **pooled** connection string for the Vercel serverless backend. Do not rerun the migration against an already populated target; the script protects against copying into a non-empty application database. Full instructions are in [Deployment](docs/deployment.md).

## Security and operational boundaries

- Never commit `.env`, `.env.local`, `DATABASE_URL`, API keys, administrator passwords, SQLite files or database exports.
- Rotate the backend bearer key in both Vercel projects together if it is exposed.
- Use separate strong values for the backend API key and frontend administrator password.
- The current UI/API has one shared inventory space; there is no user/tenant separation.
- SQLAlchemy `create_all` initializes tables; there is no Alembic migration history yet. Introduce versioned migrations before evolving the production schema.
- Vercel Firewall/System Mitigations are separate from application authentication. A Vercel challenge/403 is not the same as the app's Basic Auth 401. See [Operations runbook](docs/operations-runbook.md).

## Repository guide

```text
stockout-radar/
├── .github/workflows/ci.yml       # Backend and frontend CI checks
├── data/                          # Raw/processed data ignored; templates and sample tracked
├── docs/                           # Architecture, API, deployment, model, security, testing
├── frontend/                       # Next.js App Router application
├── models/                         # Saved model artifacts
├── notebooks/                      # Original data/ML analysis notebooks
├── reports/                        # Evaluation metrics and figures
├── scripts/                        # Forecast refresh, assessment, migration and audits
├── src/main.py                     # Vercel FastAPI entrypoint
├── src/stockout_radar/             # Forecasting, features, inventory and API modules
├── tests/                          # Pytest suite
├── requirements*.txt               # Python dependency sets
└── README.md
```

## Contributors and academic context

This repository extends the original Stockout Radar academic project into a full-stack demonstrator. The original project repository is [ManahilFatima16/stockout-radar](https://github.com/ManahilFatima16/stockout-radar); the maintained fork is [smaharx/stockout-radar](https://github.com/smaharx/stockout-radar).

| Contributor | Project contribution (as recorded in the project README) |
|---|---|
| Muhammad Qasim | Project lead and ML pipeline |
| Shahzaib Mahar | Data preprocessing |
| Manahil Fatima | Model development and original application work |

## Licence

The **dataset** is distributed under CC BY 4.0 by UCI. The repository does not currently contain a software `LICENSE` file, so no MIT or other software licence is claimed. See [Licensing notes](docs/licensing.md). Do not add an MIT licence unless the relevant copyright holders have agreed that the repository code may be released under those terms.

## Acknowledgements

- Chen, D. (2012). *Online Retail II*. UCI Machine Learning Repository. [Dataset page](https://archive.ics.uci.edu/dataset/502/online+retail).
- The original Stockout Radar project contributors and the academic project team.
