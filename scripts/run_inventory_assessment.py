"""Generate inventory recommendations from a completed inventory CSV."""

import argparse
from pathlib import Path

import pandas as pd

from stockout_radar.inventory import assess_inventory
from stockout_radar.inventory_io import load_inventory_inputs


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FORECAST_PATH = (
    ROOT / "reports" / "outputs" / "forecast_snapshot.csv"
)

DEFAULT_INVENTORY_PATH = (
    ROOT / "data" / "templates" / "inventory_input_completed.csv"
)

DEFAULT_OUTPUT_PATH = (
    ROOT / "reports" / "outputs" / "inventory_recommendations.csv"
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Stockout Radar inventory recommendations."
    )
    parser.add_argument(
        "--forecast",
        type=Path,
        default=DEFAULT_FORECAST_PATH,
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=DEFAULT_INVENTORY_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )

    args = parser.parse_args()

    if not args.forecast.is_file():
        raise FileNotFoundError(
            f"Forecast snapshot not found: {args.forecast}"
        )

    forecasts = pd.read_csv(
        args.forecast,
        dtype={"StockCode": "string"},
        parse_dates=[
            "history_through_week",
            "forecast_start_week",
        ],
    )

    inventory = load_inventory_inputs(args.inventory)

    print(f"Products with inventory supplied: {len(inventory):,}")

    recommendations = assess_inventory(
        forecasts,
        inventory,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    recommendations.to_csv(args.output, index=False)

    print("\nINVENTORY ASSESSMENT")
    print("--------------------")
    print("Products assessed:", len(recommendations))
    print(
        "Reorder now:",
        int((recommendations["risk_status"] == "REORDER_NOW").sum()),
    )
    print(
        "Watch:",
        int((recommendations["risk_status"] == "WATCH").sum()),
    )
    print(
        "Healthy:",
        int((recommendations["risk_status"] == "HEALTHY").sum()),
    )
    print(
        "Total suggested units:",
        int(recommendations["recommended_order_qty"].sum()),
    )

    print("\nTOP REORDER RECOMMENDATIONS")

    columns = [
        "StockCode",
        "forecast_4week_demand",
        "current_stock",
        "reorder_point",
        "risk_status",
        "recommended_order_qty",
    ]

    print(
        recommendations.loc[
            recommendations["reorder_required"], columns
        ]
        .sort_values(
            "recommended_order_qty",
            ascending=False,
        )
        .head(15)
        .to_string(index=False)
    )

    print(f"\nFull report saved: {args.output}")


if __name__ == "__main__":
    main()
