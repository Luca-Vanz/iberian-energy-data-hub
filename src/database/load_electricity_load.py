import argparse
import sqlite3
from pathlib import Path

import pandas as pd


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


def create_electricity_load_table():
    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS electricity_load (
                timestamp_utc TEXT NOT NULL,
                timestamp_market TEXT NOT NULL,
                market_date TEXT NOT NULL,
                period INTEGER NOT NULL,
                country TEXT NOT NULL,
                load_mw REAL NOT NULL,
                source TEXT NOT NULL,
                interval_minutes INTEGER NOT NULL,

                PRIMARY KEY (
                    timestamp_utc,
                    country
                )
            )
            """
        )

    print(
        "Electricity load table ready."
    )


def load_processed_file(
    processed_path: Path,
):
    if not processed_path.exists():
        raise FileNotFoundError(
            f"Processed load file not found: "
            f"{processed_path}"
        )

    df = pd.read_csv(
        processed_path
    )

    required_columns = {
        "timestamp_utc",
        "timestamp_market",
        "market_date",
        "period",
        "country",
        "load_mw",
        "source",
        "interval_minutes",
    }

    missing_columns = (
        required_columns
        - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Processed load file is missing "
            f"columns: {sorted(missing_columns)}"
        )

    if df.isnull().any().any():
        raise ValueError(
            "Null values found in processed "
            "electricity load data."
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.executemany(
            """
            INSERT INTO electricity_load (
                timestamp_utc,
                timestamp_market,
                market_date,
                period,
                country,
                load_mw,
                source,
                interval_minutes
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(
                timestamp_utc,
                country
            )

            DO UPDATE SET
                timestamp_market =
                    excluded.timestamp_market,

                market_date =
                    excluded.market_date,

                period =
                    excluded.period,

                load_mw =
                    excluded.load_mw,

                source =
                    excluded.source,

                interval_minutes =
                    excluded.interval_minutes
            """,
            df[
                [
                    "timestamp_utc",
                    "timestamp_market",
                    "market_date",
                    "period",
                    "country",
                    "load_mw",
                    "source",
                    "interval_minutes",
                ]
            ].itertuples(
                index=False,
                name=None,
            ),
        )

    print(
        f"Loaded {len(df)} electricity "
        f"load rows into SQLite."
    )


def load_ren_demand(
    date: str,
):
    processed_path = (
        Path("data")
        / "processed"
        / "ren"
        / f"actual_load_{date}.csv"
    )

    load_processed_file(
        processed_path
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Load standardized electricity "
            "load data into SQLite."
        )
    )

    parser.add_argument(
        "date",
        help=(
            "Market date in YYYYMMDD format."
        ),
    )

    parser.add_argument(
        "--source",
        choices=["REN"],
        default="REN",
        help=(
            "Source of the processed load data."
        ),
    )

    args = parser.parse_args()

    create_electricity_load_table()

    if args.source == "REN":
        load_ren_demand(
            date=args.date
        )


if __name__ == "__main__":
    main()