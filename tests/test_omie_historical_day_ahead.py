import sqlite3

import pandas as pd

from src.database.load_omie_historical_day_ahead import (
    _build_country_rows,
    load_rows,
)


def _worksheet():
    rows = []
    for date, count in (
        ("1998-01-01", 24),
        ("2025-03-30", 23),
        ("2025-09-30", 24),
    ):
        row = [pd.Timestamp(date)]
        row.extend(float(value) for value in range(1, count + 1))
        row.extend([None] * (25 - count))
        row.extend([0.0, "MTU60"])
        rows.append(row)

    columns = ["Date\\Hour"] + list(range(1, 26)) + [
        "Daily average",
        "Market Time Unit (MTU)",
    ]
    return pd.DataFrame(rows, columns=columns)


def test_dst_period_counts_and_database_load():
    rows = _build_country_rows(_worksheet(), "ES")

    assert len(rows) == 71
    assert rows[26][1].startswith("2025-03-30 03:00:00")

    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE omie_day_ahead_prices (
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
    load_rows(connection, rows)

    assert connection.execute(
        "SELECT COUNT(*) FROM market_price_data"
    ).fetchone()[0] == 71
    assert connection.execute(
        "SELECT DISTINCT native_resolution_minutes FROM market_price_data"
    ).fetchall() == [(60,)]
