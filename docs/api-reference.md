# API reference

## Base URL and authorization

Local base URL:

```text
http://127.0.0.1:8001/api/v1
```

Production base URL:

```text
https://stockout-radar-api.vercel.app/api/v1
```

Every route is protected by the FastAPI bearer-key dependency. In production, `STOCKOUT_RADAR_API_KEY` must be configured; the API fails closed if it is missing.

```http
Authorization: Bearer <STOCKOUT_RADAR_API_KEY>
Accept: application/json
```

The deployed Next.js frontend adds the bearer key server-side. Browser clients should use the frontend proxy rather than call the backend with a secret.

## Endpoints

| Method | Path | Success | Description |
|---|---|---:|---|
| GET | `/health` | 200 | API process and database connectivity |
| GET | `/products` | 200 | Search/paginate products with an active forecast |
| GET | `/forecasts` | 200 | Search/paginate detailed active forecasts |
| GET | `/inventory` | 200 | List saved operator inventory inputs |
| PUT | `/inventory/{stock_code}` | 200 | Insert or update inventory inputs for a forecasted product |
| POST | `/inventory/assessment` | 200 | Calculate and persist an assessment for all saved inventory |
| GET | `/inventory/assessment` | 200 | Retrieve the latest saved assessment |

## Query parameters

`GET /products` and `GET /forecasts` accept:

| Parameter | Type | Default | Validation |
|---|---|---:|---|
| `search` | string | omitted | 1–100 characters when supplied; case-insensitive substring match |
| `limit` | integer | 50 | 1–200 |
| `offset` | integer | 0 | 0 or greater |

Example:

```bash
curl -H "Authorization: Bearer $STOCKOUT_RADAR_API_KEY" \
  "http://127.0.0.1:8001/api/v1/products?search=100&limit=8&offset=0"
```

## Health

`GET /health` executes a database connectivity check.

Example response:

```json
{"status":"ok","database":"connected"}
```

A database failure returns HTTP 503. A missing or invalid production bearer token returns HTTP 401.

## Products

`GET /products` returns product codes that have a row in the active forecast run.

Response shape:

```json
{
  "items": [
    {
      "stock_code": "10080",
      "forecast_4week_demand": 14.3395,
      "forecast_start_week": "2011-12-05"
    }
  ],
  "total": 4675
}
```

The example item is illustrative of the previously migrated historical snapshot; values can differ if a new forecast run is loaded.

## Forecasts

`GET /forecasts` returns detailed active forecast records, including:

- `stock_code`
- `history_through_week`
- `forecast_start_week`
- `raw_model_prediction`
- `forecast_4week_demand` (non-negative post-processed prediction)
- `prediction_was_clipped`
- `forecast_horizon_weeks`
- `model_artifact`
- response-level `total` and `forecast_run_id`

## Inventory

`GET /inventory` returns a list with `stock_code`, `current_stock`, `lead_time_days`, `safety_stock` and `updated_at`.

`PUT /inventory/{stock_code}` creates or updates a product's inventory input. The stock code must exist in the active forecast run.

Request body:

```json
{
  "current_stock": 80,
  "lead_time_days": 7,
  "safety_stock": 20
}
```

Validation:

- `current_stock >= 0`
- `safety_stock >= 0`
- `lead_time_days` is an integer from 1 through 28
- product code must have an active forecast (otherwise HTTP 404)

The route returns the saved record, including `updated_at`.

## Assessments

`POST /inventory/assessment` calculates recommendations for all saved inventory items and persists an assessment snapshot. It does not update the inventory input records.

`GET /inventory/assessment` returns the latest assessment summary and recommendation rows. If no assessment exists, it returns HTTP 404.

Assessment summary fields:

- `assessment_run_id`
- `forecast_run_id`
- `created_at`
- `item_count`
- `reorder_now_count`
- `watch_count`
- `healthy_count`
- `total_recommended_order_qty`

Each recommendation includes current stock inputs, four-week forecast demand, average daily demand, lead-time demand, reorder point, target stock, days of cover, risk status, reorder flag, recommended order quantity and demand-estimation method.

## Error handling

| HTTP status | Meaning in this API |
|---:|---|
| 401 | Missing or invalid bearer API key |
| 404 | Product has no active forecast, or no assessment exists yet |
| 409 | No usable active forecast run |
| 422 | Invalid inventory values or invalid assessment inputs |
| 503 | Database unavailable or production API authentication not configured |

A Vercel edge `403` with `x-vercel-mitigated: challenge` is a platform security response, not an API-level error from these routes.

## Interactive documentation

Local Swagger UI: <http://127.0.0.1:8001/docs>.

The production API is bearer-protected. Do not publish the bearer token in a browser, issue, screenshot or documentation example.
