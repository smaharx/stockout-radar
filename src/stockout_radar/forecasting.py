"""Product-level four-week demand forecasting service."""

from pathlib import Path

import numpy as np
import pandas as pd

from stockout_radar.features import latest_feature_rows
from stockout_radar.model import DemandPredictor
from stockout_radar.schema import FEATURE_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_WEEKLY_PANEL_PATH = (
    PROJECT_ROOT / "data" / "processed" / "weekly_panel.csv"
)

# Use our newly trained model, not the legacy reference model.
DEFAULT_FORECAST_MODEL_PATH = (
    PROJECT_ROOT / "models" / "stockout_radar_v1.joblib"
)


class ForecastingError(RuntimeError):
    """Raised when a product-level forecast cannot be generated."""


class DemandForecastService:
    """Generate four-week demand forecasts for all products in a weekly panel."""

    def __init__(
        self,
        weekly_panel_path: str | Path = DEFAULT_WEEKLY_PANEL_PATH,
        model_path: str | Path = DEFAULT_FORECAST_MODEL_PATH,
    ) -> None:
        self.weekly_panel_path = Path(weekly_panel_path)
        self.model_path = Path(model_path)
        self.predictor = DemandPredictor(model_path=self.model_path)

    def forecast(self, weekly_panel: pd.DataFrame) -> pd.DataFrame:
        """Forecast the next four weeks for each product."""

        latest = latest_feature_rows(weekly_panel)

        if latest.empty:
            raise ForecastingError(
                "No products are available for forecasting."
            )

        features = latest.loc[:, list(FEATURE_COLUMNS)]
        raw_predictions = self.predictor.predict(features)

        raw_values = raw_predictions.to_numpy(dtype=float)

        if not np.isfinite(raw_values).all():
            raise ForecastingError(
                "The model returned non-finite forecast values."
            )

        results = latest[
            [
                "StockCode",
                "history_through_week",
                "forecast_start_week",
            ]
        ].copy()

        results["raw_model_prediction"] = raw_values

        # Demand cannot be negative. Preserve raw output for diagnostics.
        results["forecast_4week_demand"] = np.maximum(raw_values, 0.0)

        results["prediction_was_clipped"] = raw_values < 0.0
        results["forecast_horizon_weeks"] = 4
        results["model_artifact"] = self.model_path.name

        return results.sort_values(
            "StockCode"
        ).reset_index(drop=True)

    def forecast_from_file(self) -> pd.DataFrame:
        """Load the configured weekly panel and forecast every product."""

        if not self.weekly_panel_path.is_file():
            raise FileNotFoundError(
                f"Weekly panel not found: {self.weekly_panel_path}"
            )

        weekly_panel = pd.read_csv(
            self.weekly_panel_path,
            dtype={"StockCode": "string"},
            parse_dates=["week"],
        )

        return self.forecast(weekly_panel)
