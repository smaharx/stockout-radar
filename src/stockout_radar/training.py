"""Reproducible chronological training and evaluation for Stockout Radar."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from stockout_radar.schema import FEATURE_COLUMNS, TARGET_COLUMN


ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = ROOT / "data" / "processed" / "model_table.csv"
OLD_MODEL_PATH = ROOT / "models" / "gb_model.joblib"
NEW_MODEL_PATH = ROOT / "models" / "stockout_radar_v1.joblib"
REPORT_PATH = ROOT / "reports" / "metrics" / "training_evaluation.json"

GAP_WEEKS = 4
RANDOM_STATE = 42


def load_training_data() -> pd.DataFrame:
    """Load and validate the existing prepared model table."""

    required = ["StockCode", "week", TARGET_COLUMN, *FEATURE_COLUMNS]

    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Training data not found: {DATA_PATH}")

    data = pd.read_csv(
        DATA_PATH,
        usecols=required,
        dtype={"StockCode": "string"},
        parse_dates=["week"],
    )

    if data["week"].isna().any():
        raise ValueError("The model table contains missing or invalid week dates.")

    if data.duplicated(["StockCode", "week"]).any():
        raise ValueError("Duplicate StockCode/week combinations found.")

    data[TARGET_COLUMN] = pd.to_numeric(
        data[TARGET_COLUMN], errors="raise"
    )

    if data[TARGET_COLUMN].isna().any():
        raise ValueError("The target column contains missing values.")

    for column in FEATURE_COLUMNS:
        original = data[column]
        converted = pd.to_numeric(original, errors="coerce")

        invalid = original.notna() & converted.isna()
        if invalid.any():
            raise ValueError(
                f"Non-numeric values found in feature '{column}'."
            )

        data[column] = converted

    feature_values = data.loc[:, list(FEATURE_COLUMNS)].to_numpy(dtype=float)

    if np.isinf(feature_values).any():
        raise ValueError("Infinite values found in model features.")

    return data.sort_values(["week", "StockCode"]).reset_index(drop=True)


def chronological_split(data: pd.DataFrame):
    """
    Split by calendar week, never by random rows.

    Four weeks of separation are reserved between each period because
    the target represents demand over the following four weeks.
    """

    weeks = pd.DatetimeIndex(sorted(data["week"].unique()))

    if len(weeks) < 30:
        raise ValueError("Not enough distinct weeks for chronological splitting.")

    train_cut = int(len(weeks) * 0.70)
    validation_cut = int(len(weeks) * 0.85)

    train_end = weeks[train_cut - 1]
    validation_end = weeks[validation_cut - 1]

    validation_start = train_end + pd.Timedelta(weeks=GAP_WEEKS)
    test_start = validation_end + pd.Timedelta(weeks=GAP_WEEKS)

    train = data[data["week"] <= train_end].copy()

    validation = data[
        (data["week"] >= validation_start)
        & (data["week"] <= validation_end)
    ].copy()

    test = data[data["week"] >= test_start].copy()

    if train.empty or validation.empty or test.empty:
        raise ValueError(
            "A chronological split is empty. Review the available date range."
        )

    return train, validation, test, {
        "train_start": str(train["week"].min().date()),
        "train_end": str(train["week"].max().date()),
        "validation_start": str(validation["week"].min().date()),
        "validation_end": str(validation["week"].max().date()),
        "test_start": str(test["week"].min().date()),
        "test_end": str(test["week"].max().date()),
        "embargo_weeks": GAP_WEEKS,
    }


def build_models():
    """Return candidate models with preprocessing where required."""

    return {
        "Ridge Regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=10.0)),
        ]),

        "Random Forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(
                n_estimators=80,
                max_depth=14,
                min_samples_leaf=2,
                max_features=0.8,
                n_jobs=-1,
                random_state=RANDOM_STATE,
            )),
        ]),

        "Gradient Boosting": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", GradientBoostingRegressor(
                loss="huber",
                n_estimators=60,
                learning_rate=0.05,
                max_depth=2,
                random_state=RANDOM_STATE,
            )),
        ]),

        "HistGradientBoosting": HistGradientBoostingRegressor(
            loss="absolute_error",
            learning_rate=0.08,
            max_iter=150,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            random_state=RANDOM_STATE,
        ),
    }


def calculate_metrics(actual, predicted) -> dict:
    """Calculate demand forecasting metrics."""

    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    valid = np.isfinite(actual) & np.isfinite(predicted)
    actual = actual[valid]
    predicted = predicted[valid]

    if len(actual) == 0:
        raise ValueError("No valid observations available for evaluation.")

    absolute_error = np.abs(actual - predicted)
    denominator = np.sum(np.abs(actual))

    wape = (
        float(np.sum(absolute_error) / denominator * 100)
        if denominator > 0 else None
    )

    return {
        "observations": int(len(actual)),
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "wape_percent": wape,
    }


def evaluate_reference_model(X, y) -> dict:
    """Evaluate the old saved model without modifying it."""

    if not OLD_MODEL_PATH.is_file():
        return {"status": "Existing model artifact not found."}

    old_model = joblib.load(OLD_MODEL_PATH)
    predictions = old_model.predict(X)

    return {
        "model": type(old_model).__name__,
        **calculate_metrics(y, predictions),
    }


def main():
    print("Loading and validating the existing model table...")
    data = load_training_data()

    print(f"Rows available: {len(data):,}")
    print(f"Distinct weeks: {data['week'].nunique():,}")

    train, validation, test, split_info = chronological_split(data)

    X_train = train.loc[:, list(FEATURE_COLUMNS)]
    y_train = train[TARGET_COLUMN]

    X_validation = validation.loc[:, list(FEATURE_COLUMNS)]
    y_validation = validation[TARGET_COLUMN]

    X_test = test.loc[:, list(FEATURE_COLUMNS)]
    y_test = test[TARGET_COLUMN]

    print("\nChronological split:")
    print(f"Training rows:   {len(train):,}")
    print(f"Validation rows: {len(validation):,}")
    print(f"Test rows:       {len(test):,}")
    print(f"Embargo:         {GAP_WEEKS} weeks")

    validation_results = {}

    baseline_predictions = (
        validation["units_mean4"].to_numpy(dtype=float) * 4
    )
    validation_results["Moving Average Baseline"] = calculate_metrics(
        y_validation, baseline_predictions
    )

    print("\nEvaluating the existing saved model...")
    validation_results["Existing Saved Model"] = evaluate_reference_model(
        X_validation, y_validation
    )

    print("\nTraining new candidate models...")
    models = build_models()

    for name, model in models.items():
        print(f"\nTraining: {name}")
        model.fit(X_train, y_train)

        predictions = model.predict(X_validation)
        validation_results[name] = calculate_metrics(
            y_validation, predictions
        )

        print(validation_results[name])

    # Select only from newly trained models, using validation MAE.
    best_name = min(
        models,
        key=lambda name: validation_results[name]["mae"],
    )

    print(f"\nSelected candidate: {best_name}")

    # Refit using the training and validation periods.
    # The embargo periods remain excluded.
    fit_data = pd.concat([train, validation], ignore_index=True)

    final_model = models[best_name]
    final_model.fit(
        fit_data.loc[:, list(FEATURE_COLUMNS)],
        fit_data[TARGET_COLUMN],
    )

    # Evaluate once on the untouched test period.
    print("\nEvaluating selected model on the held-out test period...")
    test_results = {
        "Selected New Model": calculate_metrics(
            y_test, final_model.predict(X_test)
        ),
        "Moving Average Baseline": calculate_metrics(
            y_test,
            test["units_mean4"].to_numpy(dtype=float) * 4,
        ),
        "Existing Saved Model": evaluate_reference_model(X_test, y_test),
    }

    ROOT.joinpath("models").mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save separately. Never overwrite the original gb_model.joblib.
    joblib.dump(final_model, NEW_MODEL_PATH)

    report = {
        "selected_model": best_name,
        "feature_columns": list(FEATURE_COLUMNS),
        "target": TARGET_COLUMN,
        "split": split_info,
        "validation_results": validation_results,
        "test_results": test_results,
        "training_rows": int(len(fit_data)),
        "scikit_learn_version": sklearn.__version__,
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2))

    print("\nTRAINING COMPLETE")
    print(f"New model saved: {NEW_MODEL_PATH}")
    print(f"Evaluation report saved: {REPORT_PATH}")

    print("\nHeld-out test results:")
    for name, metrics in test_results.items():
        print(f"{name}: {metrics}")


if __name__ == "__main__":
    main()
