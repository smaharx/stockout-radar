"""Generate a forecast snapshot and blank inventory input template."""

from pathlib import Path

from stockout_radar.forecasting import DemandForecastService
from stockout_radar.inventory_io import save_inventory_template


ROOT = Path(__file__).resolve().parents[1]

TEMPLATE_PATH = (
    ROOT / "data" / "templates" / "inventory_input_template.csv"
)

FORECAST_PATH = (
    ROOT / "reports" / "outputs" / "forecast_snapshot.csv"
)


def main():
    print("Generating product forecasts...")

    forecasts = DemandForecastService().forecast_from_file()

    FORECAST_PATH.parent.mkdir(parents=True, exist_ok=True)
    forecasts.to_csv(FORECAST_PATH, index=False)

    print(f"Forecast records saved: {len(forecasts):,}")
    print(f"Forecast snapshot: {FORECAST_PATH}")

    save_inventory_template(
        forecasts["StockCode"],
        TEMPLATE_PATH,
    )

    print(f"Inventory template: {TEMPLATE_PATH}")
    print(f"Products in template: {len(forecasts):,}")

    print("\nTemplate columns:")
    print("StockCode, current_stock, lead_time_days, safety_stock")

    print("\nFill in the three inventory fields for the products you manage.")
    print("Leave products without inventory information blank.")


if __name__ == "__main__":
    main()
