# Operations runbook

## Service URLs

- Frontend: <https://stockout-radar.vercel.app>
- Backend: <https://stockout-radar-api.vercel.app>
- Backend health route: `/api/v1/health` (bearer protected)
- Local Swagger UI: <http://127.0.0.1:8001/docs>

## Routine health check

The backend health response verifies a database round-trip (`SELECT 1`). It does not validate forecast freshness or the quality of the ML model.

```bash
BACKEND_URL="https://stockout-radar-api.vercel.app"
read -rsp "Backend API key: " API_KEY; echo
curl -i -H "Authorization: Bearer $API_KEY" "$BACKEND_URL/api/v1/health"
unset API_KEY
```

Expected JSON:

```json
{"status":"ok","database":"connected"}
```

## Routine application check

1. Open the production frontend.
2. Authenticate as the configured administrator.
3. Check the dashboard's backend connection indicator.
4. Open Demand forecasts and confirm the expected active forecast run/date/horizon.
5. Open Inventory and review operator-entered stock values.
6. Open Reorder recommendations and check the latest assessment identifier/time.
7. Before running a new assessment, confirm the inventory inputs are current and complete.

## Running an assessment

A new assessment snapshots the current inventory inputs against the active forecast run. It writes a new `assessment_runs` row and associated `inventory_recommendations` rows. It does not modify `inventory_items`.

Recommended operator sequence:

1. Confirm stock counts and supplier lead times from trusted sources.
2. Update only the products that have an active forecast.
3. Check that every lead time is between 1 and 28 days.
4. Run the assessment once.
5. Review REORDER_NOW/WATCH/HEALTHY classifications and suggested quantities.
6. Apply human review before placing any order.

## Refreshing forecasts

A refresh is an explicit batch operation, not a normal web request. Validate the new weekly panel and model artifact, preserve the current run/database state, run `scripts/refresh_forecasts.py` against the intended database, and inspect the newly active run. The source repository's current prepared forecast snapshot is historical; a fresh dataset and retrained/revalidated model are required for current-market forecasts.

## Troubleshooting

| Symptom | Likely layer | Checks |
|---|---|---|
| Frontend returns HTTP 401 | Application Basic Auth or backend auth depending on path | Verify the frontend username/password variables and the request path. A homepage 401 without credentials is expected. |
| Frontend returns HTTP 403 and `x-vercel-mitigated: challenge` | Vercel edge Firewall/System Mitigation | Inspect Firewall → Traffic → challenged event; record request ID; test an alternate network; contact Vercel if false-positive continues. Do not reset app credentials for an edge challenge. |
| Backend returns HTTP 401 with bearer message | FastAPI API-key dependency | Ensure frontend `STOCKOUT_RADAR_API_KEY` exactly matches backend `STOCKOUT_RADAR_API_KEY`; redeploy both projects after changes. |
| Backend returns HTTP 503 for database | Database connectivity/configuration | Verify production `DATABASE_URL` is present, is PostgreSQL (not SQLite), and is the correct Neon pooled URL for runtime. Check Neon compute state and backend runtime logs. |
| Frontend proxy returns HTTP 502 | Next.js could not reach FastAPI | Verify `STOCKOUT_RADAR_API_URL`, backend deployment status, backend health and runtime logs. |
| Product update returns HTTP 404 | Product does not exist in active forecast run | Search/select a product from the forecast catalogue; do not type an arbitrary SKU. |
| Assessment returns HTTP 422 | Invalid or incomplete inventory inputs | Check non-negative stock/safety stock, integer lead time 1–28, and all inventory codes have active forecasts. |
| Assessment list returns HTTP 404 | No assessment has been saved | Add at least one valid inventory row and run an assessment. |
| UI displays “Local environment” on production | Old frontend build or environment label has not been updated | The release patch makes the label derive from `NODE_ENV`; confirm the latest production deployment contains the updated frontend bundle. |

## Secret rotation

If the backend bearer key is exposed:

1. Generate a fresh random key on a trusted machine.
2. Update `STOCKOUT_RADAR_API_KEY` in the backend Vercel Production environment.
3. Update the same exact value in the frontend Vercel Production environment.
4. Redeploy both Vercel projects.
5. Verify that unauthenticated backend requests return 401 and authenticated health returns 200.
6. Revoke/remove the old key from any secret store where it was retained.

If the administrator password is exposed, update only `STOCKOUT_RADAR_ADMIN_PASSWORD` in the frontend Production environment and redeploy the frontend. Do not reuse the backend API key as the administrator password.

## Backup and schema operations

- Use the Neon provider's available backup/restore facilities and verify recovery procedures before relying on the database for important data.
- Export important forecast and assessment snapshots before destructive maintenance.
- There is no Alembic migration history in this release. The application currently initializes SQLAlchemy tables with `create_all`; avoid ad-hoc production schema changes. Adopt versioned migrations before evolving the schema.
- Do not rerun the one-time SQLite migration against an already-populated target.
