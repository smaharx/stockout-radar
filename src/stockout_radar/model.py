"""Loading and inference for the saved Stockout Radar demand model."""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from stockout_radar.schema import FEATURE_COLUMNS, PREDICTION_COLUMN


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "gb_model.joblib"


class ModelArtifactError(RuntimeError):
    """Raised when the saved model cannot be loaded or does not match its schema."""


class PredictionInputError(ValueError):
    """Raised when prediction input does not match the required feature schema."""


class DemandPredictor:
    """Load the saved model and generate four-week demand predictions."""

    def __init__(self, model_path: str | Path = DEFAULT_MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self._model = None

    def load(self):
        """Load the model once and verify its expected feature schema."""
        if self._model is not None:
            return self._model

        if not self.model_path.is_file():
            raise ModelArtifactError(
                f"Model artifact was not found: {self.model_path}"
            )

        try:
            model = joblib.load(self.model_path)
        except Exception as exc:
            raise ModelArtifactError(
                f"Could not load model artifact: {self.model_path}"
            ) from exc

        expected_count = getattr(model, "n_features_in_", None)
        if expected_count != len(FEATURE_COLUMNS):
            raise ModelArtifactError(
                f"Model expects {expected_count} features; "
                f"the project schema defines {len(FEATURE_COLUMNS)}."
            )

        model_features = getattr(model, "feature_names_in_", None)
        if model_features is not None:
            actual = tuple(str(name) for name in model_features)
            if actual != FEATURE_COLUMNS:
                raise ModelArtifactError(
                    "Model feature names or order do not match the project schema."
                )

        self._model = model
        return self._model

    def predict(self, feature_rows: pd.DataFrame) -> pd.Series:
        """
        Predict four-week demand from rows containing the 16 model features.

        Extra columns are ignored. Missing feature values are retained as NaN,
        which the saved HistGradientBoostingRegressor supports.
        """
        if not isinstance(feature_rows, pd.DataFrame):
            raise PredictionInputError("Input must be a pandas DataFrame.")

        if feature_rows.empty:
            raise PredictionInputError("Input contains no rows.")

        if feature_rows.columns.duplicated().any():
            raise PredictionInputError("Input contains duplicate column names.")

        missing = [
            column for column in FEATURE_COLUMNS
            if column not in feature_rows.columns
        ]
        if missing:
            raise PredictionInputError(
                f"Missing required model features: {missing}"
            )

        selected = feature_rows.loc[:, list(FEATURE_COLUMNS)].copy()
        numeric = selected.apply(pd.to_numeric, errors="coerce")

        invalid = selected.notna() & numeric.isna()
        if invalid.any().any():
            bad_column = invalid.columns[invalid.any()][0]
            bad_index = invalid.index[invalid[bad_column]][0]
            raise PredictionInputError(
                f"Non-numeric value in feature '{bad_column}' "
                f"at input index {bad_index!r}."
            )

        values = numeric.to_numpy(dtype=float)
        if np.isinf(values).any():
            raise PredictionInputError(
                "Input contains infinite feature values."
            )

        predictions = np.asarray(self.load().predict(numeric), dtype=float)

        if predictions.ndim != 1 or len(predictions) != len(feature_rows):
            raise ModelArtifactError(
                "Model returned an unexpected prediction shape."
            )

        return pd.Series(
            predictions,
            index=feature_rows.index,
            name=PREDICTION_COLUMN,
        )
