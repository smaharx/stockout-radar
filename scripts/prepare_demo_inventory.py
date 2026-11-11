"""Generate explicitly synthetic inventory data for a demonstration."""

from pathlib import Path
import math

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

FORECAST_PATH = ROOT / "reports" / "outputs" / "forecast_snapshot.csv"
OUTPUT_PATH = ROOT / "data" / "samples" / "synthetic_inventory_demo.csv"


def main():
    if not FORECAST_PATH.is_file():
        raise FileNotFoundError(
            "Forecast snapshot not found. Run prepare_inventory_inputs.py first."
        )

    forecasts = pd.read_csv(
        FORECAST_PATH,
        dtype={"StockCode": "string"},
    )

    # Select 30 products with sufficient forecast demand to demonstrate
    # all three inventory statuses clearly.
    sample = (
        forecasts.loc[
            forecasts["forecast_4week_demand"] > 20
        ]
        .sort_values("forecast_4week_demand", ascending=False)
        .head(30)
        .reset_index(drop=True)
    )

    if len(sample) < 30:
        raise ValueError(
            "Fewer than 30 products have forecast demand above 20 units. "
            "Review the available forecast data before creating the demo."
        )

    records = []

    for index, row in sample.iterrows():
        demand = float(row["forecast_4week_demand"])
        lead_time = [7, 14, 21][index % 3]
        safety_stock = max(5, math.ceil(demand * 0.10))

        reorder_point = (
            demand / 28 * lead_time + safety_stock
        )
        target_stock = demand + safety_stock

        if index < 10:
            # Synthetic scenario: inventory below reorder point.
            current_stock = math.floor(reorder_point)

        elif index < 20:
            # Synthetic scenario: above reorder point but below target.
            current_stock = math.ceil(
                (reorder_point + target_stock) / 2
            )

        else:
            # Synthetic scenario: inventory above target stock.
            current_stock = math.ceil(
                target_stock + max(5, target_stock * 0.25)
            )

        records.append({
            "StockCode": row["StockCode"],
            "current_stock": current_stock,
            "lead_time_days": lead_time,
            "safety_stock": safety_stock,
        })

    output = pd.DataFrame(records)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_PATH, index=False)

    print("SYNTHETIC DEMONSTRATION INVENTORY CREATED")
    print("This is simulated data, not actual retailer inventory.")
    print("Products:", len(output))
    print("Output:", OUTPUT_PATH)
    print("\nSample:")
    print(output.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
