import argparse
import sqlite3
from pathlib import Path

import pandas as pd


DATABASE_PATH = Path("data") / "database" / "iberian_energy.db"


def create_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS omie_day_ahead_prices (
                timestamp_utc TEXT NOT NULL,
                timestamp_market TEXT NOT NULL,
                market_date TEXT NOT NULL,
                period INTEGER NOT NULL,
                bidding_zone TEXT NOT NULL,
                price_eur_mwh REAL NOT NULL,

                PRIMARY KEY (timestamp_utc, bidding_zone)
            )
            """
        )

    print(f"Database ready: {DATABASE_PATH}")


def load_omie_prices(date: str):
    processed_path = (
        Path("data")
        / "processed"
        / "omie"
        / f"day_ahead_prices_{date}.csv"
    )

    if not processed_path.exists():
        raise FileNotFoundError(
            f"Processed OMIE file not found: {processed_path}"
        )

    df = pd.read_csv(processed_path)

    es_df = df[
        [
            "timestamp_utc",
            "timestamp_market",
            "period",
            "price_es_eur_mwh",
        ]
    ].copy()

    es_df["bidding_zone"] = "ES"

    es_df = es_df.rename(
        columns={
            "price_es_eur_mwh": "price_eur_mwh"
        }
    )

    pt_df = df[
        [
            "timestamp_utc",
            "timestamp_market",
            "period",
            "price_pt_eur_mwh",
        ]
    ].copy()

    pt_df["bidding_zone"] = "PT"

    pt_df = pt_df.rename(
        columns={
            "price_pt_eur_mwh": "price_eur_mwh"
        }
    )

    database_df = pd.concat(
        [es_df, pt_df],
        ignore_index=True,
    )

    database_df["market_date"] = date

    database_df = database_df[
        [
            "timestamp_utc",
            "timestamp_market",
            "market_date",
            "period",
            "bidding_zone",
            "price_eur_mwh",
        ]
    ]

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.executemany(
            """
            INSERT INTO omie_day_ahead_prices (
                timestamp_utc,
                timestamp_market,
                market_date,
                period,
                bidding_zone,
                price_eur_mwh
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(timestamp_utc, bidding_zone)
            DO UPDATE SET
                timestamp_market = excluded.timestamp_market,
                market_date = excluded.market_date,
                period = excluded.period,
                price_eur_mwh = excluded.price_eur_mwh
            """,
            database_df.itertuples(
                index=False,
                name=None,
            ),
        )

    print(
        f"Loaded {len(database_df)} rows "
        f"into SQLite for {date}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Load processed OMIE prices into SQLite."
    )

    parser.add_argument(
        "date",
        help="Market date in YYYYMMDD format.",
    )

    args = parser.parse_args()

    create_database()
    load_omie_prices(args.date)


if __name__ == "__main__":
    main()