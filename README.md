# Stockout Radar

**Machine-learning demand forecasting and inventory replenishment decision support for small retailers.**

Stockout Radar is an academic full-stack project that combines historical sales forecasting with operator-provided inventory information to produce replenishment recommendations.

> **Scope and limitation:** Stockout Radar forecasts product demand and applies inventory rules to recommend replenishment. The source dataset does not contain historical inventory balances or stockout labels, so this project does not directly predict or validate actual stockout events.

## Project overview

The application uses the Online Retail II transaction dataset to build weekly product-demand features and generate an aggregate four-week demand forecast for each product. Users provide current stock, supplier lead time, and safety stock. The inventory engine combines these inputs with the forecast to estimate lead-time demand, calculate a reorder point, and recommend an order quantity.

The project contains:

- A Python demand-forecasting and evaluation pipeline.
- A FastAPI REST API.
- SQLAlchemy database models and persistence services.
- SQLite for local development and PostgreSQL for hosted operation.
- A Next.js, React, and TypeScript web application.
- Inventory management and saved replenishment assessments.
- Backend automated tests and frontend type, lint, and production-build checks.

## Architecture

```text
Online Retail II historical transactions
                  |
                  v
        Cleaning and weekly aggregation
                  |
                  v
       Weekly product demand features
                  |
                  v
       Trained machine-learning model
                  |
                  v
         Four-week demand forecasts
                  |
                  v
             Forecast database
                  |
        +---------+----------+
        |                    |
        v                    v
  Forecast records     User inventory inputs
                       - Current stock
                       - Lead time
                       - Safety stock
        |                    |
        +---------+----------+
                  |
                  v
         Inventory assessment
                  |
                  v
       Replenishment recommendations
                  |
                  v
              FastAPI
                  |
                  v
          Next.js frontend
```

## Technology stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Data processing | Pandas, NumPy |
| Machine learning | Scikit-learn |
| Model serialization | Joblib |
| API | FastAPI |
| Database access | SQLAlchemy |
| Local database | SQLite |
| Hosted database | PostgreSQL / Neon |
| Frontend | Next.js, React, TypeScript |
| UI icons | Lucide React |
| Backend tests | Pytest |
| Frontend checks | TypeScript, ESLint, Next.js build |
| Version control | Git and GitHub |
| Deployment target | Vercel |

## Dataset

The project uses **Online Retail II** from the UCI Machine Learning Repository.

- Dataset: https://archive.ics.uci.edu/dataset/502/online+retail
- License: CC BY 4.0
- Historical transaction period: 1 December 2009 to 9 December 2011.
- The raw dataset is not stored in this repository. Download it separately when reproducing the data-preparation and training workflow.

The cleaned project data excludes cancellations, non-positive quantities and prices, and non-product transaction codes. The weekly product panel contains 4,675 products and 407,702 product-weeks before model-row filtering.

## Forecasting methodology

The forecasting workflow constructs a weekly product-level panel and engineers 16 features, including:

- Recent sales lags.
- Rolling demand means and standard deviations.
- Order-count features.
- Price and price-change features.
- Demand trend features.
- Calendar and product-age features.

The target is the total number of product units sold over the next four weeks. Features use information available before the forecast period. The evaluation uses chronological data splits and a moving-average baseline.

The current forecast service uses the saved model artifact:

```text
models/stockout_radar_v1.joblib
```

The legacy artifact `models/gb_model.joblib` is retained for compatibility with the original project code. The current forecasting service explicitly loads `stockout_radar_v1.joblib`.

## Evaluation results

The current chronological holdout evaluation produced these aggregate results:

| Model | MAE | RMSE | WAPE |
|---|---:|---:|---:|
| Selected model | 59.2246 | 236.0493 | 47.7349% |
| Four-week moving-average baseline | 66.1085 | 236.2273 | 53.2833% |

These metrics describe aggregate holdout performance and are not accuracy guarantees for individual products. The selected model outperformed the moving-average baseline on the aggregate measures shown, but did so for approximately 40.3% of evaluated products (1,809 of 4,484). Performance varies across products, and sudden high-volume demand spikes remain difficult to forecast.

Evaluation figures and selected metric summaries are stored under `reports/`.

## Inventory and recommendation logic

The user supplies three inventory inputs:

- `current_stock`: on-hand quantity.
- `lead_time_days`: supplier replenishment lead time.
- `safety_stock`: additional buffer quantity.

The assessment engine uses the four-week forecast to estimate average daily demand and lead-time demand. The core calculations are:

```text
Average daily demand = Four-week forecast / 28
Lead-time demand = Average daily demand × Lead time
Reorder point = Lead-time demand + Safety stock
```

The engine also calculates a target stock level, estimated days of cover, and recommended order quantity. Recommendations are classified as `HEALTHY`, `WATCH`, or `REORDER_NOW`.

These outputs are decision-support recommendations. An inventory operator should review them before placing a purchase order.

## Historical-data limitations

The source sales data ends on 9 December 2011. The migrated demonstration forecast run records history through 28 November 2011 and a forecast start week of 5 December 2011. These are historical demonstration forecasts, not current-market predictions.

Other limitations include:

1. The dataset contains sales transactions but no historical inventory balances or observed stockout events.
2. The forecast cannot be validated against actual historical stockout outcomes.
3. Sudden bulk orders and demand changes can produce substantial forecast errors.
4. Product-level model performance varies; aggregate metrics should not be interpreted as per-product accuracy guarantees.
5. Products with insufficient sales history may not receive a model forecast.

A live operational use case requires current sales ingestion, a controlled forecast-refresh schedule, ongoing evaluation, and appropriate operational review.

## Repository structure

```text
stockout-radar/
├── data/
│   ├── raw/                       # Downloaded source data; not committed
│   ├── processed/                 # Generated data; not committed
│   ├── samples/                   # Small synthetic demonstration data
│   └── templates/                 # Inventory input template
├── frontend/
│   ├── app/                       # Overview, forecasts, inventory, recommendations
│   ├── components/
│   ├── lib/
│   └── package.json
├── models/                        # Saved model artifacts
├── notebooks/                     # Original analysis and ML notebooks
├── reports/
│   ├── figures/
│   ├── metrics/
│   └── outputs/
├── scripts/                       # Forecast, evaluation and migration utilities
├── src/
│   ├── main.py                    # FastAPI deployment entrypoint
│   └── stockout_radar/
│       ├── api/
│       ├── features.py
│       ├── forecasting.py
│       ├── inventory.py
│       ├── model.py
│       └── training.py
├── tests/
├── requirements.txt
├── requirements-backend.txt
└── requirements-dev.txt
```

## Local development

### Prerequisites

- Python 3.12.
- Node.js 20.9 or newer.
- npm and Git.

### 1. Clone the repository

```bash
git clone https://github.com/smaharx/stockout-radar.git
cd stockout-radar
```

### 2. Create and activate the Python environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-backend.txt
pip install -r requirements-dev.txt
```

The backend dependency file pins the numerical and model-related package versions used by the saved model artifact.

### 4. Configure local environment variables

```bash
cp .env.example .env
```

Local development defaults to SQLite when `DATABASE_URL` is not set and `APP_ENV=local`. Do not commit `.env` or any real credentials.

### 5. Prepare the forecasting inputs

A new forecast run requires:

- `data/processed/weekly_panel.csv`
- `models/stockout_radar_v1.joblib`

The raw and processed datasets are intentionally excluded from Git. Download and prepare the UCI dataset using the project's data-preparation notebooks before regenerating forecasts.

### 6. Generate and store forecasts

```bash
PYTHONPATH=src python scripts/refresh_forecasts.py
```

This batch command generates four-week forecasts and persists a forecast run to the database configured by `DATABASE_URL` (or the local SQLite default).

### 7. Start the backend

From the repository root:

```bash
source .venv/bin/activate
APP_ENV=local python -m uvicorn stockout_radar.api.main:app \
  --reload --app-dir src --port 8001
```

- API base: http://127.0.0.1:8001/api/v1
- Interactive API documentation: http://127.0.0.1:8001/docs
- Health endpoint: http://127.0.0.1:8001/api/v1/health

### 8. Install and start the frontend

In another terminal:

```bash
cd frontend
npm ci
```

Create `frontend/.env.local` with:

```dotenv
STOCKOUT_RADAR_API_URL=http://127.0.0.1:8001
```

Start Next.js:

```bash
npm run dev
```

Open http://localhost:3000.

## API endpoints

All backend endpoints use the `/api/v1` prefix.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Application and database health |
| GET | `/products` | Forecasted products |
| GET | `/forecasts` | Product forecast records |
| GET | `/inventory` | Inventory records |
| PUT | `/inventory/{stock_code}` | Create or update an inventory record |
| POST | `/inventory/assessment` | Generate and save an assessment |
| GET | `/inventory/assessment` | Retrieve the latest saved assessment |

Production API endpoints require a bearer API key. The deployed frontend additionally uses an administrator HTTP Basic Authentication gate. This is a single-administrator demonstration safeguard, not a multi-user identity or role-based access-management system.

## Testing

From the repository root:

```bash
source .venv/bin/activate
APP_ENV=local PYTHONPATH=src python -m pytest -q
python -m pip check
```

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run lint
npm run build
```

## Deployment

The deployment target uses two Vercel projects connected to this GitHub repository and a Neon PostgreSQL database.

| Vercel project | Root directory | Function region |
|---|---|---|
| Backend | `src` | `sin1` (Singapore) |
| Frontend | `frontend` | `sin1` (Singapore) |

The repository contains project-specific `vercel.json` files for the two roots. Configure the following server-side environment variables in the Vercel backend project:

- `APP_ENV=production`
- `DATABASE_URL`: Neon pooled PostgreSQL connection string.
- `STOCKOUT_RADAR_API_KEY`: private bearer token.

Configure the following in the Vercel frontend project:

- `STOCKOUT_RADAR_API_URL`: deployed backend URL.
- `STOCKOUT_RADAR_API_KEY`: the same private bearer token used by the backend.
- `STOCKOUT_RADAR_ADMIN_USER`: administrator username.
- `STOCKOUT_RADAR_ADMIN_PASSWORD`: strong administrator password.

Never commit actual environment-variable values, database connection strings, or passwords.

### SQLite to PostgreSQL migration

The one-time migration utility is:

```bash
APP_ENV=production PYTHONPATH=src \
python scripts/migrate_sqlite_to_postgres.py
```

Set `DATABASE_URL` to the **direct** Neon connection string when running the migration. Use the **pooled** Neon connection string for the deployed serverless backend. The migration utility refuses to copy into a target containing existing application records and verifies the migrated row counts.

The Vercel Hobby plan is intended for personal, non-commercial use. Review the provider's current limits before using this application for commercial workloads.

## Project contributors

This project builds on the original Stockout Radar academic work.

| Contributor | Original project responsibility |
|---|---|
| Muhammad Qasim | Project lead and ML pipeline |
| Shahzaib Mahar | Data preprocessing |
| Manahil Fatima | Model development and original application work |

The original project repository is https://github.com/ManahilFatima16/stockout-radar. The maintained full-stack fork is https://github.com/smaharx/stockout-radar.

## Acknowledgements

The Online Retail II dataset is provided by the UCI Machine Learning Repository under the CC BY 4.0 license. See the submitted academic report for the complete acknowledgements and AI-use disclosure.