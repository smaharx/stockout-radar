"""Create and read inventory input files for Stockout Radar."""

from pathlib import Path

import pandas as pd

from stockout_radar.inventory import InventoryInputError


INVENTORY_INPUT_COLUMNS = (
    "StockCode",
    "current_stock",
    "lead_time_days",
    "safety_stock",
)


def build_inventory_template(stock_codes) -> pd.DataFrame:
    """Create one blank inventory input row per unique product."""

    codes = pd.Series(stock_codes, dtype="string").dropna().str.strip()
    codes = codes[codes != ""]

    if codes.empty:
        raise InventoryInputError("No valid product codes were supplied.")

    codes = codes.drop_duplicates().sort_values()

    return pd.DataFrame({
        "StockCode": codes.reset_index(drop=True),
        "current_stock": pd.NA,
        "lead_time_days": pd.NA,
        "safety_stock": pd.NA,
    })


def save_inventory_template(
    stock_codes,
    output_path: str | Path,
) -> Path:
    """Write a blank inventory template to CSV."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    template = build_inventory_template(stock_codes)
    template.to_csv(path, index=False)

    return path


def load_inventory_inputs(input_path: str | Path) -> pd.DataFrame:
    """
    Read a completed inventory CSV.

    Rows with all three inventory fields blank are ignored, allowing a
    retailer to provide inventory data for only the products they manage.
    Partially completed rows are retained and rejected by the inventory
    validation layer.
    """

    path = Path(input_path)

    if not path.is_file():
        raise FileNotFoundError(f"Inventory input file not found: {path}")

    data = pd.read_csv(
        path,
        dtype={"StockCode": "string"},
        keep_default_na=True,
    )

    missing = [
        column for column in INVENTORY_INPUT_COLUMNS
        if column not in data.columns
    ]
    if missing:
        raise InventoryInputError(
            f"Inventory file is missing columns: {missing}"
        )

    data = data.loc[:, list(INVENTORY_INPUT_COLUMNS)].copy()

    for column in ("current_stock", "lead_time_days", "safety_stock"):
        data[column] = data[column].replace(
            r"^\s*$", pd.NA, regex=True
        )

    input_fields = [
        "current_stock",
        "lead_time_days",
        "safety_stock",
    ]

    # Ignore products for which no inventory data has been entered.
    empty_rows = data[input_fields].isna().all(axis=1)
    data = data.loc[~empty_rows].reset_index(drop=True)

    if data.empty:
        raise InventoryInputError(
            "No inventory quantities have been entered in the file."
        )

    return data
