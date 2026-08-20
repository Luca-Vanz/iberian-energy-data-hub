from __future__ import annotations

import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    REPO_ROOT
    / "data"
    / "database"
    / "iberian_energy.db"
)

RAW_ROOT = (
    REPO_ROOT
    / "data"
    / "raw"
    / "omie"
    / "intraday_auction"
)


DATES = [
    "20260802",
    "20260803",
    "20260804",
    "20260805",
    "20260806",
]

SESSION = 1


def print_separator(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def check_raw_files() -> None:
    print_separator("1. RAW OMIE FILES")

    if not RAW_ROOT.exists():
        print(f"Raw folder does not exist: {RAW_ROOT}")
        return

    all_files = list(
        RAW_ROOT.rglob("*")
    )

    for date in DATES:
        pattern = (
            f"marginalpibc_{date}"
            f"{SESSION:02d}"
        )

        matches = [
            path
            for path in all_files
            if path.is_file()
            and pattern in path.name
        ]

        print()
        print(f"{date} session {SESSION}")

        if not matches:
            print("  RAW FILE: NOT FOUND")
            continue

        for path in sorted(matches):
            print(
                f"  RAW FILE: {path.relative_to(REPO_ROOT)}"
            )
            print(
                f"  SIZE: {path.stat().st_size:,} bytes"
            )


def connect() -> sqlite3.Connection:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def check_unified_rows(
    connection: sqlite3.Connection,
) -> None:
    print_separator(
        "2. UNIFIED market_price_data ROWS"
    )

    for date in DATES:
        source_id = (
            f"marginalpibc_"
            f"{date}"
            f"{SESSION:02d}"
        )

        row = connection.execute(
            """
            SELECT
                COUNT(*) AS row_count,
                MIN(timestamp_market) AS first_timestamp,
                MAX(timestamp_market) AS last_timestamp,
                MIN(market_date) AS min_market_date,
                MAX(market_date) AS max_market_date,
                MIN(period) AS min_period,
                MAX(period) AS max_period
            FROM market_price_data
            WHERE market = 'intraday_auction'
              AND country = 'ES'
              AND session = ?
              AND source_id = ?
            """,
            (
                SESSION,
                source_id,
            ),
        ).fetchone()

        print()
        print(
            f"{date} session {SESSION}"
        )
        print(
            f"  source_id: {source_id}"
        )
        print(
            f"  rows: {row['row_count']}"
        )
        print(
            f"  first timestamp: "
            f"{row['first_timestamp']}"
        )
        print(
            f"  last timestamp: "
            f"{row['last_timestamp']}"
        )
        print(
            f"  min market_date: "
            f"{row['min_market_date']}"
        )
        print(
            f"  max market_date: "
            f"{row['max_market_date']}"
        )
        print(
            f"  period range: "
            f"{row['min_period']} "
            f"to {row['max_period']}"
        )


def check_rows_by_market_date(
    connection: sqlite3.Connection,
) -> None:
    print_separator(
        "3. ROWS GROUPED BY market_date"
    )

    placeholders = ",".join(
        "?"
        for _ in DATES
    )

    rows = connection.execute(
        f"""
        SELECT
            market_date,
            session,
            country,
            COUNT(*) AS row_count,
            COUNT(DISTINCT source_id)
                AS source_ids,
            MIN(source_id) AS first_source_id,
            MAX(source_id) AS last_source_id
        FROM market_price_data
        WHERE market = 'intraday_auction'
          AND country = 'ES'
          AND session = ?
          AND market_date IN ({placeholders})
        GROUP BY
            market_date,
            session,
            country
        ORDER BY market_date
        """,
        (
            SESSION,
            *DATES,
        ),
    ).fetchall()

    if not rows:
        print(
            "No rows found for these market dates."
        )
        return

    for row in rows:
        print()
        print(
            f"market_date: "
            f"{row['market_date']}"
        )
        print(
            f"  rows: "
            f"{row['row_count']}"
        )
        print(
            f"  source IDs: "
            f"{row['source_ids']}"
        )
        print(
            f"  first source_id: "
            f"{row['first_source_id']}"
        )
        print(
            f"  last source_id: "
            f"{row['last_source_id']}"
        )


def check_timestamp_dates(
    connection: sqlite3.Connection,
) -> None:
    print_separator(
        "4. ROWS GROUPED BY timestamp_market DATE"
    )

    rows = connection.execute(
        """
        SELECT
            SUBSTR(
                timestamp_market,
                1,
                10
            ) AS delivery_date,

            COUNT(*) AS row_count,

            COUNT(DISTINCT source_id)
                AS source_ids,

            MIN(source_id)
                AS first_source_id,

            MAX(source_id)
                AS last_source_id

        FROM market_price_data

        WHERE market = 'intraday_auction'
          AND country = 'ES'
          AND session = ?

          AND SUBSTR(
                timestamp_market,
                1,
                10
              )
              BETWEEN '2026-08-02'
                  AND '2026-08-06'

        GROUP BY
            delivery_date

        ORDER BY
            delivery_date
        """,
        (
            SESSION,
        ),
    ).fetchall()

    if not rows:
        print(
            "No rows found by timestamp_market."
        )
        return

    for row in rows:
        print()
        print(
            f"delivery_date: "
            f"{row['delivery_date']}"
        )
        print(
            f"  rows: "
            f"{row['row_count']}"
        )
        print(
            f"  source IDs: "
            f"{row['source_ids']}"
        )
        print(
            f"  first source_id: "
            f"{row['first_source_id']}"
        )
        print(
            f"  last source_id: "
            f"{row['last_source_id']}"
        )


def check_nearby_source_ids(
    connection: sqlite3.Connection,
) -> None:
    print_separator(
        "5. ALL SESSION-1 SOURCE IDs AROUND THESE DATES"
    )

    rows = connection.execute(
        """
        SELECT
            source_id,
            COUNT(*) AS row_count,
            MIN(timestamp_market)
                AS first_timestamp,
            MAX(timestamp_market)
                AS last_timestamp,
            MIN(market_date)
                AS min_market_date,
            MAX(market_date)
                AS max_market_date

        FROM market_price_data

        WHERE market = 'intraday_auction'
          AND country = 'ES'
          AND session = 1

          AND source_id
              BETWEEN
                  'marginalpibc_2026080101'
              AND
                  'marginalpibc_2026080701'

        GROUP BY
            source_id

        ORDER BY
            source_id
        """
    ).fetchall()

    if not rows:
        print(
            "No nearby source IDs found."
        )
        return

    for row in rows:
        print()
        print(
            f"{row['source_id']}"
        )
        print(
            f"  rows: "
            f"{row['row_count']}"
        )
        print(
            f"  first: "
            f"{row['first_timestamp']}"
        )
        print(
            f"  last: "
            f"{row['last_timestamp']}"
        )
        print(
            f"  market_date: "
            f"{row['min_market_date']} "
            f"to "
            f"{row['max_market_date']}"
        )


def main() -> None:
    print()
    print(
        "Iberian Energy Data Hub"
    )
    print(
        "Intraday Auction Date Diagnostic"
    )

    print(
        f"Database: {DATABASE_PATH}"
    )

    print(
        f"Raw root: {RAW_ROOT}"
    )

    check_raw_files()

    connection = connect()

    try:
        check_unified_rows(
            connection
        )

        check_rows_by_market_date(
            connection
        )

        check_timestamp_dates(
            connection
        )

        check_nearby_source_ids(
            connection
        )

    finally:
        connection.close()

    print()
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()