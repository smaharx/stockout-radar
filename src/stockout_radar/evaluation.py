"""Held-out evaluation and lightweight model monitoring for Stockout Radar.

This module reuses the project's saved model and the exact chronological split
implemented in ``stockout_radar.training``. It never fits or changes a model.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn

from stockout_radar.schema import FEATURE_COLUMNS, TARGET_COLUMN
from stockout_radar.training import (
    NEW_MODEL_PATH,
    REPORT_PATH as TRAINING_REPORT_PATH,
    chronological_split,
    load_training_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "metrics"
DEFAULT_FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"


def calculate_forecast_metrics(actual: Any, predicted: Any) -> dict[str, Any]:
    """Return MAE, RMSE, WAPE and signed forecast-bias measures.

    Residual is defined as actual - predicted. Positive residual means
    under-forecasting; negative residual means over-forecasting.
    """
    y_true = np.asarray(actual, dtype=float)
    y_pred = np.asarray(predicted, dtype=float)

    if y_true.ndim != 1 or y_pred.ndim != 1:
        raise ValueError("Actual and predicted values must be one-dimensional.")
    if y_true.shape != y_pred.shape:
        raise ValueError("Actual and predicted arrays must have the same length.")

    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]
    if y_true.size == 0:
        raise ValueError("No finite observations available for evaluation.")

    residual = y_true - y_pred
    absolute_error = np.abs(residual)
    actual_denominator = float(np.abs(y_true).sum())
    total_residual = float(residual.sum())
    total_actual = float(y_true.sum())
    total_predicted = float(y_pred.sum())

    return {
        "observations": int(y_true.size),
        "mae": float(absolute_error.mean()),
        "rmse": float(np.sqrt(np.mean(np.square(residual)))),
        "wape_percent": (
            float(absolute_error.sum() / actual_denominator * 100)
            if actual_denominator > 0 else None
        ),
        "total_actual_units": total_actual,
        "total_absolute_error_units": float(absolute_error.sum()),
        "total_predicted_units": total_predicted,
        "total_residual_actual_minus_predicted_units": total_residual,
        "net_forecast_bias_predicted_minus_actual_units": float(-total_residual),
        "mean_residual_actual_minus_predicted_units": float(residual.mean()),
    }


def _group_metrics(frame: pd.DataFrame, group_column: str, prefix: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for group_value, group in frame.groupby(group_column, sort=True, dropna=False):
        metrics = calculate_forecast_metrics(group["actual_units"], group[prefix])
        rows.append({group_column: group_value, **metrics})
    return pd.DataFrame(rows)


def build_product_evaluation(predictions: pd.DataFrame) -> pd.DataFrame:
    """Calculate product-level model and baseline metrics."""
    model = _group_metrics(predictions, "StockCode", "predicted_units")
    baseline = _group_metrics(predictions, "StockCode", "moving_average_baseline_units")

    model = model.rename(columns={
        "observations": "model_observations",
        "mae": "model_mae",
        "rmse": "model_rmse",
        "wape_percent": "model_wape_percent",
        "total_actual_units": "actual_units",
        "total_absolute_error_units": "model_total_absolute_error_units",
        "total_predicted_units": "model_predicted_units",
        "total_residual_actual_minus_predicted_units": "model_total_residual_units",
        "net_forecast_bias_predicted_minus_actual_units": "model_net_bias_units",
        "mean_residual_actual_minus_predicted_units": "model_mean_residual_units",
    })
    baseline = baseline.rename(columns={
        "observations": "baseline_observations",
        "mae": "baseline_mae",
        "rmse": "baseline_rmse",
        "wape_percent": "baseline_wape_percent",
        "total_actual_units": "baseline_actual_units_check",
        "total_absolute_error_units": "baseline_total_absolute_error_units",
        "total_predicted_units": "baseline_predicted_units",
        "total_residual_actual_minus_predicted_units": "baseline_total_residual_units",
        "net_forecast_bias_predicted_minus_actual_units": "baseline_net_bias_units",
        "mean_residual_actual_minus_predicted_units": "baseline_mean_residual_units",
    })

    result = model.merge(baseline, on="StockCode", how="inner")
    result["mae_improvement_vs_baseline_units"] = result["baseline_mae"] - result["model_mae"]
    result["wape_improvement_vs_baseline_percentage_points"] = (
        result["baseline_wape_percent"] - result["model_wape_percent"]
    )
    result["model_better_than_baseline_by_mae"] = result["model_mae"] < result["baseline_mae"]
    result = result.drop(columns=["baseline_actual_units_check"])
    return result.sort_values("model_mae", ascending=False).reset_index(drop=True)


def _json_safe(value: Any) -> Any:
    """Convert NumPy/Pandas values and non-finite numbers to JSON-safe values."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if np.isfinite(number) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value


def _write_plot_files(predictions: pd.DataFrame, weekly: pd.DataFrame, figures_dir: Path) -> list[str]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    # log1p keeps zero-demand observations visible while compressing bulk spikes.
    actual_log = np.log1p(predictions["actual_units"].clip(lower=0))
    predicted_log = np.log1p(predictions["predicted_units"].clip(lower=0))
    upper = max(float(actual_log.max()), float(predicted_log.max()), 1.0)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(actual_log, predicted_log, alpha=0.18, s=9)
    ax.plot([0, upper], [0, upper], linestyle="--", linewidth=1)
    ax.set(
        xlabel="Actual four-week demand (log1p units)",
        ylabel="Predicted four-week demand (log1p units)",
        title="Held-out test: predicted vs actual demand",
    )
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    path = figures_dir / "holdout_actual_vs_predicted.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved.append(str(path))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(predictions["residual_units"], bins=70)
    ax.axvline(0, linestyle="--", linewidth=1)
    ax.set(
        xlabel="Residual (actual − predicted units)",
        ylabel="Number of product-weeks",
        title="Held-out test: residual distribution",
    )
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    path = figures_dir / "holdout_residual_distribution.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved.append(str(path))

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(weekly["week"], weekly["mae"], marker="o")
    ax.set(
        xlabel="Prediction week", ylabel="MAE (units)",
        title="Weekly holdout monitoring: mean absolute error",
    )
    ax.tick_params(axis="x", rotation=35)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    path = figures_dir / "holdout_weekly_mae.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved.append(str(path))

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(weekly["week"], weekly["wape_percent"], marker="o")
    ax.set(
        xlabel="Prediction week", ylabel="WAPE (%)",
        title="Weekly holdout monitoring: weighted absolute percentage error",
    )
    ax.tick_params(axis="x", rotation=35)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    path = figures_dir / "holdout_weekly_wape.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved.append(str(path))

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(weekly["week"], weekly["actual_units"], marker="o", label="Actual demand")
    ax.plot(weekly["week"], weekly["predicted_units"], marker="o", label="Model forecast")
    ax.set(
        xlabel="Prediction week", ylabel="Four-week demand units",
        title="Weekly holdout monitoring: actual vs predicted total demand",
    )
    ax.tick_params(axis="x", rotation=35)
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    path = figures_dir / "holdout_weekly_actual_vs_predicted.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved.append(str(path))
    return saved


def _compare_with_saved_training_report(metrics: dict[str, Any]) -> dict[str, Any]:
    if not TRAINING_REPORT_PATH.is_file():
        return {"available": False, "matches_saved_test_metrics": None}

    with TRAINING_REPORT_PATH.open("r", encoding="utf-8") as file:
        saved = json.load(file)
    expected = saved.get("test_results", {}).get("Selected New Model", {})
    comparisons: dict[str, Any] = {}
    matches = bool(expected)
    for key in ("observations", "mae", "rmse", "wape_percent"):
        if key not in expected or key not in metrics:
            matches = False
            continue
        observed = metrics[key]
        reference = expected[key]
        same = (
            observed == reference if key == "observations"
            else abs(float(observed) - float(reference)) <= 1e-6
        )
        comparisons[key] = {
            "current": observed,
            "saved_training_report": reference,
            "matches": same,
        }
        matches = matches and same

    return {
        "available": True,
        "matches_saved_test_metrics": matches,
        "comparison": comparisons,
    }


def run_evaluation(
    model_path: str | Path = NEW_MODEL_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    figures_dir: str | Path = DEFAULT_FIGURES_DIR,
) -> dict[str, Any]:
    """Run diagnostics on the existing held-out test period; do not train."""
    model_path = Path(model_path)
    output_dir = Path(output_dir)
    figures_dir = Path(figures_dir)

    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    if not figures_dir.is_absolute():
        figures_dir = PROJECT_ROOT / figures_dir
    if not model_path.is_file():
        raise FileNotFoundError(f"Saved model artifact not found: {model_path}")

    print("Loading the existing prepared model table...")
    data = load_training_data()
    _train, _validation, test, split_info = chronological_split(data)
    print(f"Held-out test: {split_info['test_start']} to {split_info['test_end']}")
    print(f"Test rows: {len(test):,} | products: {test['StockCode'].nunique():,}")

    print(f"Loading saved model: {model_path}")
    model = joblib.load(model_path)
    expected_features = getattr(model, "n_features_in_", None)
    if expected_features != len(FEATURE_COLUMNS):
        raise ValueError(
            f"Model expects {expected_features} features; project schema has {len(FEATURE_COLUMNS)}."
        )
    model_features = getattr(model, "feature_names_in_", None)
    if model_features is not None and tuple(map(str, model_features)) != FEATURE_COLUMNS:
        raise ValueError("Saved model feature names/order do not match FEATURE_COLUMNS.")

    X_test = test.loc[:, list(FEATURE_COLUMNS)]
    actual = test[TARGET_COLUMN].to_numpy(dtype=float)
    model_prediction = np.asarray(model.predict(X_test), dtype=float)
    baseline_prediction = test["units_mean4"].to_numpy(dtype=float) * 4

    predictions = test[["StockCode", "week"]].copy()
    predictions["actual_units"] = actual
    predictions["predicted_units"] = model_prediction
    predictions["moving_average_baseline_units"] = baseline_prediction
    predictions["residual_units"] = predictions["actual_units"] - predictions["predicted_units"]
    predictions["absolute_error_units"] = predictions["residual_units"].abs()
    predictions["baseline_residual_units"] = (
        predictions["actual_units"] - predictions["moving_average_baseline_units"]
    )

    model_metrics = calculate_forecast_metrics(actual, model_prediction)
    baseline_metrics = calculate_forecast_metrics(actual, baseline_prediction)
    product_metrics = build_product_evaluation(predictions)

    weekly_rows: list[dict[str, Any]] = []
    for week, group in predictions.groupby("week", sort=True):
        model_week = calculate_forecast_metrics(group["actual_units"], group["predicted_units"])
        baseline_week = calculate_forecast_metrics(
            group["actual_units"], group["moving_average_baseline_units"]
        )
        weekly_rows.append({
            "week": week,
            "observations": model_week["observations"],
            "mae": model_week["mae"],
            "rmse": model_week["rmse"],
            "wape_percent": model_week["wape_percent"],
            "actual_units": model_week["total_actual_units"],
            "predicted_units": model_week["total_predicted_units"],
            "baseline_mae": baseline_week["mae"],
            "baseline_wape_percent": baseline_week["wape_percent"],
            "net_forecast_bias_units": model_week["net_forecast_bias_predicted_minus_actual_units"],
        })
    weekly = pd.DataFrame(weekly_rows).sort_values("week").reset_index(drop=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_dir / "holdout_predictions.csv", index=False)
    product_metrics.to_csv(output_dir / "product_level_evaluation.csv", index=False)
    weekly.to_csv(output_dir / "weekly_monitoring.csv", index=False)

    under = predictions[predictions["residual_units"] > 0].nlargest(20, "residual_units")
    over = predictions[predictions["residual_units"] < 0].nsmallest(20, "residual_units")
    under.to_csv(output_dir / "largest_under_predictions.csv", index=False)
    over.to_csv(output_dir / "largest_over_predictions.csv", index=False)

    figures = _write_plot_files(predictions, weekly, figures_dir)
    report = {
        "project": "Stockout Radar",
        "evaluation_type": "retrospective held-out test evaluation",
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model_artifact": str(model_path),
        "scikit_learn_version": sklearn.__version__,
        "split": split_info,
        "test_products": int(test["StockCode"].nunique()),
        "selected_model_metrics": model_metrics,
        "moving_average_baseline_metrics": baseline_metrics,
        "mae_improvement_vs_baseline_units": float(baseline_metrics["mae"] - model_metrics["mae"]),
        "wape_improvement_vs_baseline_percentage_points": (
            float(baseline_metrics["wape_percent"] - model_metrics["wape_percent"])
            if baseline_metrics["wape_percent"] is not None and model_metrics["wape_percent"] is not None
            else None
        ),
        "product_diagnostics": {
            "products_evaluated": int(len(product_metrics)),
            "products_model_better_by_mae": int(product_metrics["model_better_than_baseline_by_mae"].sum()),
            "products_model_worse_or_equal_by_mae": int((~product_metrics["model_better_than_baseline_by_mae"]).sum()),
            "largest_total_absolute_error_products": product_metrics.nlargest(10, "model_total_absolute_error_units")[
                ["StockCode", "model_mae", "model_wape_percent", "model_total_absolute_error_units"]
            ].to_dict(orient="records"),
        },
        "saved_training_report_comparison": _compare_with_saved_training_report(model_metrics),
        "residual_sign_convention": "actual - predicted; positive means under-forecast, negative means over-forecast",
        "monitoring_note": (
            "Weekly metrics are computed retrospectively on the historical held-out test period. "
            "For live monitoring, actual sales must be joined to forecasts after the four-week horizon matures. "
            "Adjacent weekly forecast origins have overlapping four-week target windows, so weekly points are not independent."
        ),
        "artifacts": {
            "predictions_csv": str(output_dir / "holdout_predictions.csv"),
            "product_metrics_csv": str(output_dir / "product_level_evaluation.csv"),
            "weekly_monitoring_csv": str(output_dir / "weekly_monitoring.csv"),
            "largest_under_predictions_csv": str(output_dir / "largest_under_predictions.csv"),
            "largest_over_predictions_csv": str(output_dir / "largest_over_predictions.csv"),
            "figures": figures,
        },
    }
    report = _json_safe(report)
    report_path = output_dir / "holdout_evaluation.json"
    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, allow_nan=False)

    print("\nEvaluation complete.")
    print(f"Model MAE:       {model_metrics['mae']:.4f}")
    print(f"Model RMSE:      {model_metrics['rmse']:.4f}")
    print(f"Model WAPE:      {model_metrics['wape_percent']:.4f}%")
    print(f"Baseline MAE:    {baseline_metrics['mae']:.4f}")
    print(f"Baseline WAPE:   {baseline_metrics['wape_percent']:.4f}%")
    print(
        "Products better than baseline by MAE: "
        f"{report['product_diagnostics']['products_model_better_by_mae']:,}/{len(product_metrics):,}"
    )
    print(f"Saved report: {report_path}")
    print(f"Saved diagnostics: {output_dir}")
    print(f"Saved figures: {figures_dir}")
    comparison = report["saved_training_report_comparison"]
    if comparison.get("available"):
        print(f"Matches saved training test metrics: {comparison['matches_saved_test_metrics']}")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the saved Stockout Radar model on its held-out test set."
    )
    parser.add_argument("--model-path", default=str(NEW_MODEL_PATH), help="Saved model artifact path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for evaluation CSV/JSON files.")
    parser.add_argument("--figures-dir", default=str(DEFAULT_FIGURES_DIR), help="Directory for evaluation figures.")
    args = parser.parse_args(argv)
    run_evaluation(args.model_path, args.output_dir, args.figures_dir)
