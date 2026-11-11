#!/usr/bin/env python3
"""One-time migration of Stockout Radar SQLite data to PostgreSQL."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.types import DateTime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stockout_radar.api.database import Base, make_engine  # noqa: E402
from stockout_radar.api import db_models as _db_models  # noqa: E402,F401


TABLE_ORDER = (
    "forecast_runs",
    "product_forecasts",
    "inventory_items",
    "assessment_runs",
    "inventory_recommendations",
)

SEQUENCE_TABLES = (
    "forecast_runs",
    "product_forecasts",
    "assessment_runs",
    "inventory_recommendations",
)


def normalize_row(table, mapping):
    """Normalize SQLite timestamps for PostgreSQL timezone-aware columns."""
    record = dict(mapping)

    for column in table.columns:
        if not isinstance(column.type, DateTime):
            continue

        if not column.type.timezone:
            continue

        value = record.get(column.name)

        if value is None:
            continue

        if value.tzinfo is None:
            record[column.name] = value.replace(tzinfo=timezone.utc)
        else:
            record[column.name] = value.astimezone(timezone.utc)

    return record


def count_rows(connection, table):
    return int(
        connection.execute(
            select(func.count()).select_from(table)
        ).scalar_one()
    )


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Stockout Radar SQLite records into PostgreSQL."
    )

    default_source = f"sqlite:///{ROOT / 'stockout_radar.db'}"

    parser.add_argument(
        "--source-url",
        default=default_source,
        help="Source SQLite URL. Defaults to the project stockout_radar.db.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
    )

    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1.")

    target_url = os.getenv("DATABASE_URL", "").strip()

    if not target_url:
        parser.error("DATABASE_URL must contain the Neon PostgreSQL connection URL.")

    if not target_url.startswith(
        ("postgres://", "postgresql://", "postgresql+psycopg://")
    ):
        parser.error("Target DATABASE_URL must use PostgreSQL with psycopg.")

    source_path = ROOT / "stockout_radar.db"

    if args.source_url == default_source and not source_path.is_file():
        parser.error(f"SQLite database not found: {source_path}")

    source_connect_args = (
        {"check_same_thread": False}
        if args.source_url.startswith("sqlite")
        else {}
    )

    source_engine = create_engine(
        args.source_url,
        connect_args=source_connect_args,
    )

    # Use the central URL normalizer so postgresql:// selects psycopg v3.
    target_engine = make_engine()

    try:
        source_tables = set(inspect(source_engine).get_table_names())
        missing = sorted(set(TABLE_ORDER) - source_tables)

        if missing:
            raise RuntimeError(
                f"Source database is missing required tables: {missing}"
            )

        # Create an empty target schema before copying data.
        Base.metadata.create_all(bind=target_engine)

        with target_engine.connect() as target:
            occupied = {
                name: count_rows(target, Base.metadata.tables[name])
                for name in TABLE_ORDER
            }

        if any(occupied.values()):
            raise RuntimeError(
                "Migration aborted: target PostgreSQL database is not empty. "
                f"Existing row counts: {occupied}"
            )

        copied = {}

        with source_engine.connect() as source, target_engine.begin() as target:
            for table_name in TABLE_ORDER:
                table = Base.metadata.tables[table_name]

                rows = source.execute(
                    select(table).order_by(*list(table.primary_key.columns))
                ).mappings()

                total = 0

                while True:
                    batch = rows.fetchmany(args.batch_size)

                    if not batch:
                        break

                    payload = [
                        normalize_row(table, row)
                        for row in batch
                    ]

                    target.execute(table.insert(), payload)
                    total += len(payload)

                copied[table_name] = total
                print(f"Copied {table_name}: {total} records")

            # Explicit IDs do not automatically advance PostgreSQL sequences.
            for table_name in SEQUENCE_TABLES:
                table = Base.metadata.tables[table_name]

                sequence_name = target.scalar(
                    text(
                        "SELECT pg_get_serial_sequence(:table_name, 'id')"
                    ),
                    {"table_name": table_name},
                )

                if not sequence_name:
                    continue

                maximum_id = target.scalar(
                    select(func.max(table.c.id))
                )

                target.execute(
                    text(
                        "SELECT setval("
                        "CAST(:sequence_name AS regclass), "
                        ":last_value, :is_called)"
                    ),
                    {
                        "sequence_name": sequence_name,
                        "last_value": maximum_id if maximum_id is not None else 1,
                        "is_called": maximum_id is not None,
                    },
                )

        with target_engine.connect() as target:
            final_counts = {
                name: count_rows(target, Base.metadata.tables[name])
                for name in TABLE_ORDER
            }

        if copied != final_counts:
            raise RuntimeError(
                "Post-migration row-count validation failed. "
                f"Copied={copied}; Target={final_counts}"
            )

        print("\nMigration completed and verified.")
        print("Final PostgreSQL record counts:")

        for name, count in final_counts.items():
            print(f"  {name}: {count}")

    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    main()
