# Testing and acceptance

## Automated backend tests

The last user-run local verification recorded **40 passing pytest tests** with one Starlette/httpx deprecation warning. Re-run the suite on the current checkout before making a new release:

```bash
source .venv/bin/activate
APP_ENV=local PYTHONPATH=src python -m pytest -q
python -m pip check
```

The test modules cover:

- Feature engineering and leakage-safe feature construction.
- Forecast and model interfaces.
- Inventory calculations and inventory file input/output.
- API endpoints and persistence behaviour.
- Backend API-key security.
- Production database URL guards.
- Evaluation metric calculations.

## Frontend checks

From `frontend/`:

```bash
npm ci
npm run typecheck
npm run lint
npm run build
```

These checks cover TypeScript compilation, ESLint rules and an optimized Next.js production build. They do not constitute browser-based end-to-end tests.

## Continuous integration

`.github/workflows/ci.yml` runs backend tests and frontend checks on pushes to `main`, pull requests targeting `main`, and manual workflow dispatch. GitHub Actions status is displayed by the CI badge in the README.

## Production acceptance checklist

Run after a new frontend/backend deployment or a change to production configuration.

### Access and authentication

- [ ] Production frontend domain resolves over HTTPS.
- [ ] Unauthenticated homepage request reaches the application auth gate and returns HTTP 401 (unless Vercel edge protection intercepts it).
- [ ] Correct administrator credentials return HTTP 200.
- [ ] Backend request without bearer key returns HTTP 401.
- [ ] Backend request with the configured key returns HTTP 200.
- [ ] Vercel `x-vercel-mitigated: challenge` is recorded separately from app-level 401 responses.

### API and database

- [ ] `/api/v1/health` returns `status=ok` and `database=connected`.
- [ ] Products and forecasts return the expected total for the active forecast run.
- [ ] Inventory list loads.
- [ ] Latest saved assessment loads.

### Workflow

- [ ] Record current inventory inputs before write testing.
- [ ] Create/update one product with a confirmed active forecast.
- [ ] Confirm the success response and refreshed inventory table.
- [ ] Run one assessment.
- [ ] Confirm the assessed item count equals the number of tracked inventory products.
- [ ] Confirm the new assessment appears after a page reload.
- [ ] Confirm the saved data is present in PostgreSQL.
- [ ] Review all recommendations before treating them as operational guidance.

Do not repeatedly create test assessments or modify unknown real inventory values. Use a designated demo product and record original values before write testing.

## Last demonstrated production workflow

On 12 November 2026, the production UI showed Assessment #4 completed for three inventory products: three `REORDER_NOW`, zero `WATCH`, zero `HEALTHY`, and 51 suggested replenishment units. An inventory write for product `21003` was also confirmed in the UI. These figures are a demonstration snapshot, not a permanent environment invariant.
