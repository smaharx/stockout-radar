"""Compare regenerated weekly features with the existing model table."""

import numpy as np
import pandas as pd

PANEL_PATH = "data/processed/weekly_panel.csv"
MODEL_TABLE_PATH = "data/processed/model_table.csv"

FEATURES = [
    "units_lag1", "units_lag2", "units_lag4",
    "units_mean4", "units_std4", "units_mean8", "units_std8",
    "orders_lag1", "orders4", "price_lag1",
    "price_change4", "trend_ratio", "week_of_year",
    "month", "weeks_to_xmas", "product_age",
]

KEYS = ["StockCode", "week"]


def main():
    print("Reading existing datasets...")

    panel = pd.read_csv(
        PANEL_PATH,
        dtype={"StockCode": "string"},
        parse_dates=["week"],
    )

    stored = pd.read_csv(
        MODEL_TABLE_PATH,
        dtype={"StockCode": "string"},
        parse_dates=["week"],
    )

    panel = panel.sort_values(KEYS).reset_index(drop=True)

    if panel.duplicated(KEYS).any():
        raise ValueError("Weekly panel has duplicate product/week rows.")

    print(f"Weekly panel rows: {len(panel):,}")
    print(f"Model table rows:  {len(stored):,}")

    # Check whether each product has an uninterrupted weekly history.
    date_gaps = panel.groupby("StockCode")["week"].diff()
    irregular = date_gaps.notna() & (date_gaps != pd.Timedelta(days=7))

    print(f"Irregular product-week intervals: {int(irregular.sum()):,}")

    # Regenerate features using information available before each week.
    groups = panel.groupby("StockCode", sort=False)

    generated = panel[KEYS].copy()

    for lag in (1, 2, 4):
        generated[f"units_lag{lag}"] = groups["units"].shift(lag)

    for window in (4, 8):
        generated[f"units_mean{window}"] = groups["units"].transform(
            lambda values: values.shift(1).rolling(
                window, min_periods=window
            ).mean()
        )
        generated[f"units_std{window}"] = groups["units"].transform(
            lambda values: values.shift(1).rolling(
                window, min_periods=window
            ).std()
        )

    generated["orders_lag1"] = groups["orders"].shift(1)

    generated["orders4"] = groups["orders"].transform(
        lambda values: values.shift(1).rolling(4, min_periods=4).sum()
    )

    generated["price_lag1"] = groups["avg_price"].shift(1)

    # Compare the previous week's price with its price four weeks earlier.
    generated["price_change4"] = (
        groups["avg_price"].shift(1)
        / groups["avg_price"].shift(5)
        - 1
    )

    generated["trend_ratio"] = (
        (generated["units_mean4"] + 1)
        / (generated["units_mean8"] + 1)
    )

    generated["week_of_year"] = (
        panel["week"].dt.isocalendar().week.astype("int64")
    )
    generated["month"] = panel["week"].dt.month

    christmas_this_year = pd.to_datetime(
        panel["week"].dt.year.astype(str) + "-12-25"
    )
    christmas_next_year = (
        christmas_this_year + pd.DateOffset(years=1)
    )
    christmas = christmas_this_year.where(
        panel["week"] <= christmas_this_year,
        christmas_next_year,
    )

    generated["weeks_to_xmas"] = (
        (christmas - panel["week"]).dt.days // 7
    )

    first_week = groups["week"].transform("min")
    generated["product_age"] = (
        (panel["week"] - first_week).dt.days // 7
    )

    # The target covers the current week and the following three weeks.
    generated["target"] = (
        groups["units"].shift(0)
        + groups["units"].shift(-1)
        + groups["units"].shift(-2)
        + groups["units"].shift(-3)
    )

    # Match regenerated values to the stored model table.
    comparison = stored[
        KEYS + FEATURES + ["target"]
    ].merge(
        generated,
        on=KEYS,
        how="left",
        suffixes=("_stored", "_generated"),
        validate="one_to_one",
        indicator=True,
    )

    unmatched = int((comparison["_merge"] != "both").sum())
    print(f"Model-table rows without a matching panel row: {unmatched:,}")

    print("\nFeature comparison")
    print("-" * 65)

    failures = []

    for column in FEATURES + ["target"]:
        actual = pd.to_numeric(
            comparison[f"{column}_stored"], errors="coerce"
        ).to_numpy(dtype=float)

        rebuilt = pd.to_numeric(
            comparison[f"{column}_generated"], errors="coerce"
        ).to_numpy(dtype=float)

        matches = np.isclose(
            actual,
            rebuilt,
            rtol=1e-5,
            atol=1e-6,
            equal_nan=True,
        )

        mismatch_count = int((~matches).sum())
        failures.append(mismatch_count)

        print(
            f"{column:20s} "
            f"matches: {int(matches.sum()):>8,} "
            f"mismatches: {mismatch_count:>8,}"
        )

        if mismatch_count:
            example = comparison.loc[
                ~matches,
                KEYS + [
                    f"{column}_stored",
                    f"{column}_generated",
                ],
            ].head(3)

            print("  Example differences:")
            print(example.to_string(index=False))

    print("\nAUDIT SUMMARY")
    print("-" * 65)

    if unmatched == 0 and sum(failures) == 0:
        print("PASS: All stored features and targets were reproduced.")
    else:
        print("REVIEW REQUIRED: Some values did not match.")
        print("We must investigate differences before implementing inference.")


if __name__ == "__main__":
    main()
