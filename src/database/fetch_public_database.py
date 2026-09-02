from __future__ import annotations

import gzip
import os
import shutil
import sqlite3
import urllib.request
from pathlib import Path


REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

DEPLOYMENT_DIR = (
    REPO_ROOT
    / "deployment"
)

DATABASE_PATH = (
    DEPLOYMENT_DIR
    / "iberian_energy_public.db"
)

DOWNLOAD_PATH = (
    DEPLOYMENT_DIR
    / "iberian_energy_public.db.gz.download"
)

TEMP_DATABASE_PATH = (
    DEPLOYMENT_DIR
    / "iberian_energy_public.db.part"
)


DEFAULT_PUBLIC_DB_URL = (
    "https://github.com/"
    "Luca-Vanz/"
    "iberian-energy-data-hub/"
    "releases/latest/download/"
    "iberian_energy_public.db.gz"
)


EXPECTED_TABLES = {
    "balancing_market_data",
    "market_catalog_cache",
    "market_events",
    "market_price_data",
    "omie_day_ahead_prices",
}


ALLOWED_MARKETS = {
    "day_ahead",
    "intraday_auction",
    "intraday_continuous",
}

ALLOWED_BALANCING_MARKETS = {"afrr", "mfrr"}

def download_database(
    url: str,
) -> None:

    print(
        f"Downloading public database:"
    )

    print(
        f"  {url}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "iberian-energy-data-hub"
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=180,
    ) as response:

        with DOWNLOAD_PATH.open(
            "wb"
        ) as destination:

            shutil.copyfileobj(
                response,
                destination,
            )

    size_mb = (
        DOWNLOAD_PATH.stat().st_size
        / 1024
        / 1024
    )

    print(
        f"Downloaded: {size_mb:.2f} MB"
    )


def decompress_database() -> None:

    print(
        "Decompressing SQLite database..."
    )

    with gzip.open(
        DOWNLOAD_PATH,
        "rb",
    ) as source:

        with TEMP_DATABASE_PATH.open(
            "wb"
        ) as destination:

            shutil.copyfileobj(
                source,
                destination,
            )

    size_mb = (
        TEMP_DATABASE_PATH.stat().st_size
        / 1024
        / 1024
    )

    print(
        f"Decompressed: {size_mb:.2f} MB"
    )


def validate_database(
    database_path: Path,
) -> None:

    print(
        "Validating downloaded public database..."
    )

    connection = sqlite3.connect(
        database_path
    )

    try:

        integrity = (
            connection.execute(
                "PRAGMA quick_check"
            ).fetchone()[0]
        )

        if integrity != "ok":

            raise RuntimeError(
                (
                    "SQLite integrity check failed: "
                    f"{integrity}"
                )
            )


        tables = {
            row[0]
            for row
            in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        }


        if tables != EXPECTED_TABLES:

            raise RuntimeError(
                (
                    "Unexpected public database tables. "
                    f"Expected: {sorted(EXPECTED_TABLES)}. "
                    f"Found: {sorted(tables)}."
                )
            )


        sources = {
            row[0]
            for row
            in connection.execute(
                """
                SELECT DISTINCT source
                FROM market_price_data
                """
            ).fetchall()
        }


        if sources != {"OMIE"}:

            raise RuntimeError(
                (
                    "Public database contains "
                    f"unexpected sources: {sources}"
                )
            )


        markets = {
            row[0]
            for row
            in connection.execute(
                """
                SELECT DISTINCT market
                FROM market_price_data
                """
            ).fetchall()
        }


        if not markets.issubset(
            ALLOWED_MARKETS
        ):

            raise RuntimeError(
                (
                    "Public database contains "
                    f"forbidden markets: "
                    f"{sorted(markets - ALLOWED_MARKETS)}"
                )
            )


        forbidden_balancing_rows = connection.execute(
            """
            SELECT COUNT(*) FROM balancing_market_data
            WHERE NOT (
                source = 'ESIOS' AND country = 'ES'
                AND service IN ('afrr', 'mfrr')
            )
            """
        ).fetchone()[0]
        if forbidden_balancing_rows:
            raise RuntimeError(
                f"Public database contains {forbidden_balancing_rows:,} "
                "unapproved balancing rows."
            )

        balancing_catalog_count = (
            connection.execute(
                """
                SELECT payload_json
                FROM market_catalog_cache
                WHERE id = 1
                """
            ).fetchone()
        )


        if balancing_catalog_count is None:

            raise RuntimeError(
                "Market catalog cache is missing."
            )


        row_count = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM market_price_data
                """
            ).fetchone()[0]
        )


        print(
            f"Validated unified OMIE rows: "
            f"{row_count:,}"
        )

        print(
            "SQLite integrity: OK"
        )

        print(
            "Wholesale source: OMIE"
        )

        balancing_row_count = connection.execute(
            "SELECT COUNT(*) FROM balancing_market_data"
        ).fetchone()[0]
        print(f"Approved Spanish ESIOS balancing rows: {balancing_row_count:,}")

    finally:

        connection.close()


def cleanup_temporary_files() -> None:

    for path in [
        DOWNLOAD_PATH,
        TEMP_DATABASE_PATH,
    ]:

        if path.exists():

            path.unlink()


def main() -> None:

    print()
    print("=" * 72)
    print(
        "FETCH PUBLIC IBERIAN ENERGY DATABASE"
    )
    print("=" * 72)
    print()

    DEPLOYMENT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    database_url = (
        os.getenv(
            "PUBLIC_DB_URL",
            DEFAULT_PUBLIC_DB_URL,
        )
        .strip()
    )


    cleanup_temporary_files()


    try:

        download_database(
            database_url
        )

        decompress_database()

        validate_database(
            TEMP_DATABASE_PATH
        )


        os.replace(
            TEMP_DATABASE_PATH,
            DATABASE_PATH,
        )


        print()
        print(
            "Public database installed at:"
        )

        print(
            f"  {DATABASE_PATH}"
        )

        print()
        print(
            "PUBLIC DATABASE FETCH PASSED"
        )


    except Exception:

        cleanup_temporary_files()

        raise


    finally:

        if DOWNLOAD_PATH.exists():

            DOWNLOAD_PATH.unlink()


if __name__ == "__main__":
    main()
