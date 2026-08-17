import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


# ==================================================
# DATE VALIDATION
# ==================================================

def valid_date(value: str) -> str:

    try:
        datetime.strptime(
            value,
            "%Y%m%d",
        )

    except ValueError as exc:

        raise argparse.ArgumentTypeError(
            "Date must be a valid calendar "
            "date in YYYYMMDD format."
        ) from exc

    return value


# ==================================================
# CREATE TABLE
# ==================================================

def create_electricity_generation_table():

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS electricity_generation (

                timestamp_utc TEXT NOT NULL,

                timestamp_market TEXT NOT NULL,

                market_date TEXT NOT NULL,

                period INTEGER NOT NULL,

                country TEXT NOT NULL,

                technology TEXT NOT NULL,

                generation_mw REAL NOT NULL,

                source TEXT NOT NULL,

                interval_minutes INTEGER NOT NULL,

                PRIMARY KEY (
                    timestamp_utc,
                    country,
                    technology
                )
            );
            """
        )


    print(
        "Electricity generation table ready."
    )


# ==================================================
# LOAD PROCESSED FILE
# ==================================================

def load_processed_file(
    processed_path: Path,
):

    if not processed_path.exists():

        raise FileNotFoundError(
            f"Processed generation file "
            f"not found: {processed_path}"
        )


    df = pd.read_csv(
        processed_path,
        dtype={
            "market_date": str,
            "country": str,
            "technology": str,
            "source": str,
        },
    )


    required_columns = {
        "timestamp_utc",
        "timestamp_market",
        "market_date",
        "period",
        "country",
        "technology",
        "generation_mw",
        "source",
        "interval_minutes",
    }


    missing_columns = (
        required_columns
        - set(df.columns)
    )


    if missing_columns:

        raise ValueError(
            "Processed generation file is "
            "missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )


    # --------------------------------------------------
    # DATA TYPES
    # --------------------------------------------------

    df["period"] = pd.to_numeric(
        df["period"],
        errors="raise",
    ).astype(int)


    df["generation_mw"] = pd.to_numeric(
        df["generation_mw"],
        errors="raise",
    )


    df["interval_minutes"] = pd.to_numeric(
        df["interval_minutes"],
        errors="raise",
    ).astype(int)


    df["market_date"] = (
        df["market_date"]
        .astype(str)
    )


    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    if df.isnull().any().any():

        raise ValueError(
            "Null values found in processed "
            "electricity generation data."
        )


    duplicate_count = (
        df.duplicated(
            subset=[
                "timestamp_utc",
                "country",
                "technology",
            ]
        )
        .sum()
    )


    if duplicate_count > 0:

        raise ValueError(
            f"Processed file contains "
            f"{duplicate_count} duplicate "
            "generation observations."
        )


    # --------------------------------------------------
    # INSERT / UPDATE
    # --------------------------------------------------

    columns = [
        "timestamp_utc",
        "timestamp_market",
        "market_date",
        "period",
        "country",
        "technology",
        "generation_mw",
        "source",
        "interval_minutes",
    ]


    rows = list(
        df[columns]
        .itertuples(
            index=False,
            name=None,
        )
    )


    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:

        connection.executemany(
            """
            INSERT INTO electricity_generation (

                timestamp_utc,
                timestamp_market,
                market_date,
                period,
                country,
                technology,
                generation_mw,
                source,
                interval_minutes
            )

            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )

            ON CONFLICT(
                timestamp_utc,
                country,
                technology
            )

            DO UPDATE SET

                timestamp_market =
                    excluded.timestamp_market,

                market_date =
                    excluded.market_date,

                period =
                    excluded.period,

                generation_mw =
                    excluded.generation_mw,

                source =
                    excluded.source,

                interval_minutes =
                    excluded.interval_minutes;
            """,
            rows,
        )


    print(
        f"Loaded {len(df)} electricity "
        f"generation rows into SQLite."
    )


# ==================================================
# REN LOADER
# ==================================================

def load_ren_generation(
    date: str,
):

    processed_path = (
        Path("data")
        / "processed"
        / "ren"
        / "generation"
        / f"generation_{date}.csv"
    )


    load_processed_file(
        processed_path
    )


# ==================================================
# COMMAND LINE
# ==================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Load processed electricity "
            "generation data into SQLite."
        )
    )


    parser.add_argument(
        "date",
        type=valid_date,
        help=(
            "Market date in "
            "YYYYMMDD format."
        ),
    )


    parser.add_argument(
        "--source",
        choices=[
            "REN",
        ],
        default="REN",
        help=(
            "Generation data source."
        ),
    )


    args = parser.parse_args()


    create_electricity_generation_table()


    if args.source == "REN":

        load_ren_generation(
            date=args.date
        )


if __name__ == "__main__":

    main()