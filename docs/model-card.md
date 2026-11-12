# Model card: Stockout Radar four-week demand forecasting

## Summary

| Field | Description |
|---|---|
| Task | Product-level four-week aggregate unit-demand regression |
| Selected estimator | `HistGradientBoosting` (Scikit-learn) |
| Artifact | `models/stockout_radar_v1.joblib` |
| Serialized model runtime | Scikit-learn 1.8.0 |
| Input grain | One row per product and weekly forecast origin |
| Prediction | Total units demanded across four weeks |
| Serving | Batch inference, persisted to PostgreSQL, retrieved through FastAPI |

## Intended use

The model is an academic demonstration for exploring short-horizon product-demand estimation and inventory decision support. It can be used to inspect historical forecasting methodology, compare aggregate holdout metrics, and demonstrate a forecast-to-replenishment workflow using explicitly supplied inventory inputs.

It is not validated for current retail operations. It should not autonomously place purchase orders or be used as a sole basis for critical procurement decisions.

## Data provenance

The model uses Online Retail II from the UCI Machine Learning Repository. The source contains historical transactions for a UK online retailer from 1 December 2009 to 9 December 2011. The dataset is licensed CC BY 4.0. The project removes cancellations, non-positive quantity/price rows and non-product transaction codes, then creates weekly product aggregates.

The documented weekly panel contains 4,675 products and 407,702 product-weeks. After feature/target history requirements, the model table contains fewer rows. Raw and processed transaction files are not committed to the Git repository.

## Prediction target

For a product and forecast origin week `t`, the target is:

```text
units[t] + units[t+1] + units[t+2] + units[t+3]
```

This is one four-week aggregate number, not a sequence of four weekly forecasts.

## Features

The 16 features are:

| Feature | Meaning |
|---|---|
| `units_lag1` | Units in the previous week |
| `units_lag2` | Units two weeks earlier |
| `units_lag4` | Units four weeks earlier |
| `units_mean4` | Mean units over the previous four weeks |
| `units_std4` | Standard deviation of units over the previous four weeks |
| `units_mean8` | Mean units over the previous eight weeks |
| `units_std8` | Standard deviation of units over the previous eight weeks |
| `orders_lag1` | Orders in the previous week |
| `orders4` | Orders over the previous four weeks |
| `price_lag1` | Average selling price in the previous week |
| `price_change4` | Relative average-price change compared with five weeks earlier |
| `trend_ratio` | `(units_mean4 + 1) / (units_mean8 + 1)` |
| `week_of_year` | ISO week number |
| `month` | Calendar month |
| `weeks_to_xmas` | Whole weeks to the next Christmas date |
| `product_age` | Weeks since the product's first panel week |

Lagged/rolling sales, order and price features are shifted so that information from the forecast period does not enter the inputs. `latest_feature_rows` creates one inference row per product for the next unseen week after its latest observed week.

## Evaluation design

The committed retrospective evaluation uses chronological splits with a four-week embargo:

| Split | Period |
|---|---|
| Train | 1 Feb 2010 – 25 Apr 2011 |
| Validation | 23 May 2011 – 1 Aug 2011 |
| Test | 29 Aug 2011 – 7 Nov 2011 |
| Embargo | 4 weeks |

The test report contains 48,511 observations across 4,484 products. Evaluation metrics are computed over the historical holdout period.

## Holdout metrics

| Metric | Selected model | Moving-average baseline |
|---|---:|---:|
| MAE | 59.2246 | 66.1085 |
| RMSE | 236.0493 | 236.2272 |
| WAPE | 47.7349% | 53.2833% |

The model has lower aggregate MAE and WAPE than the moving-average baseline. It has lower RMSE by a small margin. Product-level diagnostics show the model has lower MAE than the baseline for 1,809 / 4,484 products (about 40.3%); it is not better for most evaluated products. Some high-volume products and sudden bulk-order spikes account for large errors.

Source of committed results: `reports/metrics/holdout_evaluation.json` and `reports/metrics/training_evaluation.json`.

## Forecast post-processing

Raw model predictions are retained for diagnostics. The forecast service clips negative values to zero because negative demand is not operationally meaningful. The database records whether a prediction was clipped.

## Known limitations and risks

1. **Historical data:** source transactions end in December 2011. The production demonstration forecast run records history through 28 November 2011 and a forecast start week of 5 December 2011. The hosted forecasts are historical demonstration outputs, not current 2026 market predictions.
2. **No stockout labels:** the dataset contains no inventory balances, stockout events or lost-sales observations. Actual stockout prediction and validation are impossible from this source alone.
3. **Product-level variation:** aggregate metrics conceal uneven product performance; the model beats the moving-average baseline by MAE for only about 40.3% of evaluated products.
4. **Bulk-order spikes:** abrupt high-volume orders are difficult to predict and can produce large errors.
5. **Cold start:** products without sufficient historical data may not receive a forecast.
6. **Stationarity and drift:** current demand patterns can differ materially from 2009–2011 behaviour.
7. **Inventory heuristic:** four-week demand is spread evenly over 28 days for lead-time demand. This is a simplifying assumption, not a learned daily-demand profile.
8. **Operational omissions:** open purchase orders, reserved stock, supplier minimum order quantities, multiple warehouses and stock transfers are not modelled.

## Appropriate interpretation

Treat each forecast and recommendation as a historical-data demonstration and decision-support estimate. Verify current sales data, on-hand quantities, supplier lead times and business constraints before any operational action. Retraining and re-evaluation on recent, representative data are prerequisites for a live-market deployment.
