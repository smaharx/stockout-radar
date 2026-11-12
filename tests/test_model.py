"""Reproducible tests for the saved Stockout Radar model."""

import unittest

import numpy as np
import pandas as pd

from stockout_radar.model import (
    DemandPredictor,
    PredictionInputError,
)
from stockout_radar.schema import (
    FEATURE_COLUMNS,
    PREDICTION_COLUMN,
)


def make_synthetic_feature_rows(row_count=5):
    """Create deterministic numeric rows matching the trained model schema."""

    data = {}

    for column_index, column in enumerate(FEATURE_COLUMNS):
        data[column] = [
            ((row_index + 1) * (column_index + 1)) / 10.0
            for row_index in range(row_count)
        ]

    return pd.DataFrame(
        data,
        columns=list(FEATURE_COLUMNS),
    )


class DemandPredictorTests(unittest.TestCase):

    def test_saved_model_predicts_from_synthetic_feature_rows(self):
        sample = make_synthetic_feature_rows()

        predictor = DemandPredictor()

        self.assertTrue(
            predictor.model_path.is_file(),
            "The saved model artifact must be available in CI.",
        )

        predictions = predictor.predict(sample)

        self.assertEqual(len(predictions), len(sample))
        self.assertEqual(predictions.name, PREDICTION_COLUMN)
        self.assertTrue(predictions.notna().all())

        self.assertTrue(
            np.isfinite(predictions.to_numpy(dtype=float)).all()
        )

    def test_missing_features_are_rejected(self):
        predictor = DemandPredictor()
        incomplete_input = pd.DataFrame({"units_lag1": [10]})

        with self.assertRaises(PredictionInputError):
            predictor.predict(incomplete_input)

    def test_non_numeric_feature_values_are_rejected(self):
        row = {
            column: 1.0
            for column in FEATURE_COLUMNS
        }

        row["units_lag1"] = "not-a-number"

        invalid_input = pd.DataFrame([row])

        predictor = DemandPredictor()

        with self.assertRaises(PredictionInputError):
            predictor.predict(invalid_input)


if __name__ == "__main__":
    unittest.main()
