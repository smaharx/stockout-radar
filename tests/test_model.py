"""Integration tests for the saved Stockout Radar model."""

import unittest
from pathlib import Path

import pandas as pd

from stockout_radar.model import DemandPredictor, PredictionInputError
from stockout_radar.schema import FEATURE_COLUMNS, PREDICTION_COLUMN


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_TABLE_PATH = PROJECT_ROOT / "data" / "processed" / "model_table.csv"


class DemandPredictorTests(unittest.TestCase):

    def test_saved_model_predicts_from_existing_model_table(self):
        self.assertTrue(MODEL_TABLE_PATH.is_file())

        sample = pd.read_csv(
            MODEL_TABLE_PATH,
            usecols=list(FEATURE_COLUMNS),
            nrows=100,
        )

        sample = sample.dropna(subset=list(FEATURE_COLUMNS)).head(5)
        self.assertFalse(sample.empty, "No complete sample rows were found.")

        predictor = DemandPredictor()
        predictions = predictor.predict(sample)

        self.assertEqual(len(predictions), len(sample))
        self.assertEqual(predictions.name, PREDICTION_COLUMN)
        self.assertTrue(predictions.notna().all())

    def test_missing_features_are_rejected(self):
        predictor = DemandPredictor()
        incomplete_input = pd.DataFrame({"units_lag1": [10]})

        with self.assertRaises(PredictionInputError):
            predictor.predict(incomplete_input)

    def test_non_numeric_feature_values_are_rejected(self):
        predictor = DemandPredictor()
        row = {column: 1.0 for column in FEATURE_COLUMNS}
        row["units_lag1"] = "not-a-number"
        invalid_input = pd.DataFrame([row])

        with self.assertRaises(PredictionInputError):
            predictor.predict(invalid_input)


if __name__ == "__main__":
    unittest.main()
