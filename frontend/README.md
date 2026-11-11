# Stockout Radar — Frontend

A production-minded Next.js dashboard for the existing Stockout Radar FastAPI backend.

## Requirements

- Node.js 20.9 or newer (Node 24 is suitable)
- npm
- The FastAPI backend running locally, by default at `http://127.0.0.1:8001`

## Install and run

From this `frontend/` directory:

```bash
cp .env.example .env.local
npm install
npm run dev
```

Open <http://localhost:3000>.

The frontend is pinned to Next.js 16.4.6 and React 19.3.1; the installed Node.js 24 runtime meets Next.js 16 requirements.

The frontend uses a same-origin Next.js Route Handler proxy. Browser requests go to `/api/backend/...`; the proxy forwards them to the backend configured by `STOCKOUT_RADAR_API_URL`. This keeps the backend origin out of browser-side code and avoids direct browser-to-backend CORS requests.

Default `.env.local` value:

```dotenv
STOCKOUT_RADAR_API_URL=http://127.0.0.1:8001
```

Do not append `/api/v1` to this setting. The proxy adds the API prefix.

## Available pages

- `/` — operations overview, API/database status, forecast run metadata, inventory risk summary and priority replenishment.
- `/forecasts` — searchable, paginated four-week product forecast catalog and current-page CSV export.
- `/inventory` — operator-entered on-hand inventory, lead time and safety-stock management.
- `/recommendations` — latest saved assessment, risk filters, order quantities and calculation notes.

## Quality checks

```bash
npm run typecheck
npm run lint
npm run build
```

## Backend contract

The UI uses the existing backend routes:

- `GET /api/v1/health`
- `GET /api/v1/products`
- `GET /api/v1/forecasts`
- `GET /api/v1/inventory`
- `PUT /api/v1/inventory/{stock_code}`
- `POST /api/v1/inventory/assessment`
- `GET /api/v1/inventory/assessment`

No backend endpoint or ML module is reimplemented in the frontend.

## Data interpretation

The forecast catalog comes from the Online Retail II dataset, whose historical transactions end in 2011. The UI explicitly labels these forecasts as historical demonstration data, not live market predictions. Inventory quantities, supplier lead times and safety-stock values are manually supplied by the operator and are not present in the source sales dataset.

## Deployment configuration

For a hosted Next.js deployment, set `STOCKOUT_RADAR_API_URL` to the backend's origin (for example, the FastAPI service URL). Keep the value server-side; do not rename it to `NEXT_PUBLIC_*`. The backend must be reachable from the Next.js server runtime. No paid hosting account is required for local development.
