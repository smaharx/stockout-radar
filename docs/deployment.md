# Production deployment runbook

## Production topology

| Component | Project | Root directory | Domain | Region |
|---|---|---|---|---|
| Next.js frontend | Vercel `stockout-radar` | `frontend` | `https://stockout-radar.vercel.app` | `sin1` |
| FastAPI backend | Vercel `stockout-radar-api` | `src` | `https://stockout-radar-api.vercel.app` | `sin1` |
| Database | Neon PostgreSQL | Managed | Private | Neon-configured region |

Both Vercel projects import `smaharx/stockout-radar` and deploy from the `main` branch. The two `vercel.json` files set the Singapore function region.

## Backend Vercel project

Configure:

- Framework/runtime: Python/FastAPI (the repository entrypoint is `src/main.py`).
- Root directory: `src`.
- Production branch: `main`.
- Region: `sin1`.

Production environment variables:

| Name | Value |
|---|---|
| `APP_ENV` | `production` |
| `DATABASE_URL` | Neon pooled PostgreSQL connection string |
| `STOCKOUT_RADAR_API_KEY` | Random, private bearer token |

The backend uses the pooled Neon URL for serverless database access. Do not paste secrets into GitHub or documentation.

## Frontend Vercel project

Configure:

- Framework: Next.js.
- Root directory: `frontend`.
- Production branch: `main`.
- Region: `sin1` (declared in `frontend/vercel.json`).

Production environment variables:

| Name | Value |
|---|---|
| `STOCKOUT_RADAR_API_URL` | `https://stockout-radar-api.vercel.app` (origin only; no `/api/v1`) |
| `STOCKOUT_RADAR_API_KEY` | Exactly the same bearer token as the backend project |
| `STOCKOUT_RADAR_ADMIN_USER` | Administrator username |
| `STOCKOUT_RADAR_ADMIN_PASSWORD` | Strong, separately generated administrator password |

The frontend `proxy.ts` uses HTTP Basic Authentication in production. The API route proxy adds the backend bearer key server-side. Do not use `NEXT_PUBLIC_` prefixes for any of these secrets.

After changing any environment variable, trigger a new Production deployment; existing deployments do not receive changed values automatically.

## Neon configuration and migration

1. Create the Neon project/database and a database role with appropriate credentials.
2. Configure the backend Vercel `DATABASE_URL` using the Neon pooled connection string.
3. For the one-time migration script, use the Neon direct (non-pooled) connection string in the local process.
4. Run the migration utility from the repository root:

```bash
source .venv/bin/activate
APP_ENV=production PYTHONPATH=src python scripts/migrate_sqlite_to_postgres.py
```

5. Review the script's count verification and then test the deployed health endpoint using the bearer key.

The migration script is intended for an empty target application database and refuses to copy into a target that already contains application rows. Do not rerun it against a populated production database. The initial migration snapshot was verified at 4,683 rows across five application tables; later production activity changes these counts.

## Forecast refresh after deployment

Forecast generation is a local/offline batch operation. The refresh script requires the prepared weekly panel and model artifact:

```bash
PYTHONPATH=src python scripts/refresh_forecasts.py
```

Before a production refresh:

- Use a reviewed and validated weekly panel from current sales data.
- Confirm the model artifact/version and compatible Scikit-learn runtime.
- Back up the database / preserve the current active run.
- Point `DATABASE_URL` deliberately at the intended target.
- Review the new run's history-through date, forecast start, horizon and product count.

Do not run a forecast refresh simply as part of a routine frontend deployment. The app currently does not schedule ingestion or retraining automatically.

## Smoke tests after deployment

Backend (use a secure local key file or a hidden prompt; do not put secrets in shell history):

```bash
BACKEND_URL="https://stockout-radar-api.vercel.app"
read -rsp "Backend API key: " API_KEY; echo
curl -sS -H "Authorization: Bearer $API_KEY" "$BACKEND_URL/api/v1/health"
unset API_KEY
```

Frontend administrator check:

```bash
FRONTEND_URL="https://stockout-radar.vercel.app"
read -rsp "Administrator password: " ADMIN_PASSWORD; echo
curl -sS -o /dev/null -w "HTTP %{http_code}\n" \
  -u "stockout-admin:$ADMIN_PASSWORD" "$FRONTEND_URL/"
unset ADMIN_PASSWORD
```

Expected: backend health responds with `status: ok` and `database: connected`; the authenticated frontend homepage returns HTTP 200. The unauthenticated frontend should return HTTP 401 from the application's Basic Auth gate when the Vercel edge does not intercept the request.

## Vercel security distinction

There are two separate layers:

1. **Application authentication:** frontend Basic Auth and backend bearer API key.
2. **Vercel Deployment Protection / Firewall:** platform-level controls which can return 401/403 before the application receives the request.

A Vercel challenge response commonly includes `x-vercel-mitigated: challenge`. This is not an incorrect application password. Keep production authentication enabled and inspect Vercel Firewall traffic/request IDs when the edge blocks a legitimate visitor. Do not disable system mitigations or add broad bypass rules as a first response.

## Rollback

If a deployment fails:

1. Keep the last known-good Production deployment available in Vercel.
2. Inspect Build Logs and Runtime Logs; record the deployment ID and request ID.
3. Revert the offending Git commit or redeploy the previous known-good build.
4. Do not change database schema or rerun a migration as a rollback shortcut.
5. Re-run backend health, authenticated frontend, API proxy and read-only data smoke tests.
