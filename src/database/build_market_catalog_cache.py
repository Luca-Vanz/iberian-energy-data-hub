from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from src.analytics.unified_prices import get_price_catalog


REPO_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    REPO_ROOT
    / "data"
    / "database"
    / "iberian_energy.db"
)


def main() -> None:
    print()
    print("Iberian Energy Data Hub")
    print("Build Market Catalog Cache")
    print("=" * 60)

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    print(f"Database: {DATABASE_PATH}")
    print()
    print(
        "Building catalog from source tables..."
    )
    print(
        "The first build may take about one minute."
    )

    started = time.perf_counter()

    catalog = get_price_catalog()

    build_seconds = (
        time.perf_counter()
        - started
    )

    wholesale = catalog.get(
        "wholesale",
        [],
    )

    balancing = catalog.get(
        "balancing",
        [],
    )

    payload_json = json.dumps(
        catalog,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    built_at_utc = (
        datetime.now(timezone.utc)
        .isoformat()
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS market_catalog_cache (
                id INTEGER PRIMARY KEY
                    CHECK (id = 1),

                payload_json TEXT NOT NULL,

                built_at_utc TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            INSERT INTO market_catalog_cache (
                id,
                payload_json,
                built_at_utc
            )
            VALUES (
                1,
                ?,
                ?
            )

            ON CONFLICT(id)
            DO UPDATE SET
                payload_json = excluded.payload_json,
                built_at_utc = excluded.built_at_utc
            """,
            (
                payload_json,
                built_at_utc,
            ),
        )

        connection.commit()

    finally:
        connection.close()

    print()
    print(
        f"Wholesale rows: {len(wholesale)}"
    )

    print(
        f"Balancing rows: {len(balancing)}"
    )

    print(
        f"Catalog build time: "
        f"{build_seconds:.3f} s"
    )

    print(
        f"Cached JSON size: "
        f"{len(payload_json):,} bytes"
    )

    print(
        f"Built at UTC: {built_at_utc}"
    )

    print()
    print(
        "MARKET CATALOG CACHE BUILT SUCCESSFULLY"
    )


if __name__ == "__main__":
    main()