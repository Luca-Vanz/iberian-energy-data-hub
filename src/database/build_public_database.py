from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

SOURCE_DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)

PUBLIC_DATABASE_PATH = (
    Path("deployment")
    / "iberian_energy_public.db"
)


# ============================================================
# PUBLIC DATA POLICY
# ============================================================

PUBLIC_MARKETS = {
    "day_ahead",
    "intraday_auction",
    "intraday_continuous",
}

PUBLIC_TABLES = {
    "balancing_market_data",
    "omie_day_ahead_prices",
    "market_price_data",
    "market_events",
    "market_catalog_cache",
    "entsoe_generation_monthly",
    "entsoe_installed_capacity",
}

COPY_BATCH_SIZE = 50_000


# ============================================================
# HELPERS
# ============================================================

def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:

    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_table_sql(
    connection: sqlite3.Connection,
    table_name: str,
) -> str:

    row = connection.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    if (
        row is None
        or row[0] is None
    ):
        raise RuntimeError(
            f"Could not find CREATE TABLE SQL "
            f"for {table_name}."
        )

    return row[0]


def get_index_sql(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    rows = connection.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'index'
          AND tbl_name = ?
          AND sql IS NOT NULL
        ORDER BY name
        """,
        (table_name,),
    ).fetchall()

    return [
        row[0]
        for row in rows
        if row[0]
    ]


def copy_query_in_batches(
    source_connection: sqlite3.Connection,
    public_connection: sqlite3.Connection,
    select_sql: str,
    insert_sql: str,
    parameters: tuple = (),
) -> int:

    cursor = source_connection.execute(
        select_sql,
        parameters,
    )

    total = 0

    while True:

        batch = cursor.fetchmany(
            COPY_BATCH_SIZE
        )

        if not batch:
            break

        public_connection.executemany(
            insert_sql,
            batch,
        )

        total += len(batch)

        print(
            f"    Copied "
            f"{total:,} rows...",
            end="\r",
        )

    print(
        f"    Copied "
        f"{total:,} rows."
    )

    return total


def readable_date(
    compact_date: str,
) -> str:

    if (
        len(compact_date) == 8
        and compact_date.isdigit()
    ):
        return (
            compact_date[:4]
            + "-"
            + compact_date[4:6]
            + "-"
            + compact_date[6:8]
        )

    return compact_date


# ============================================================
# BUILD PUBLIC CATALOG
# ============================================================

def build_public_catalog(
    connection: sqlite3.Connection,
) -> dict:

    rows = connection.execute(
        """
        SELECT
            country,
            market,
            market_stage,
            direction,
            session,
            price_unit,
            MIN(market_date),
            MAX(market_date),
            GROUP_CONCAT(
                DISTINCT native_resolution_minutes
            )

        FROM market_price_data

        GROUP BY
            country,
            market,
            market_stage,
            direction,
            session,
            price_unit

        ORDER BY
            market,
            country,
            session
        """
    ).fetchall()

    wholesale = []

    for (
        country,
        market,
        market_stage,
        direction,
        session,
        price_unit,
        first_date,
        last_date,
        resolutions_text,
    ) in rows:

        resolutions = sorted(
            {
                int(value)
                for value
                in str(
                    resolutions_text
                    or ""
                ).split(",")
                if value
            }
        )

        wholesale.append(
            {
                "country":
                    country,

                "market":
                    market,

                "market_stage":
                    market_stage,

                "direction":
                    direction,

                "session":
                    session,

                "unit":
                    price_unit,

                "first_date":
                    readable_date(
                        first_date
                    ),

                "last_date":
                    readable_date(
                        last_date
                    ),

                "native_resolutions_minutes":
                    resolutions,
            }
        )

    return {
        "wholesale":
            wholesale,

        "balancing": [
            {
                "country": row[0], "market": row[1], "market_stage": row[2],
                "metric": row[3], "direction": row[4], "unit": row[5],
                "source": row[6], "source_id": row[7],
                "first_date": readable_date(row[8]),
                "last_date": readable_date(row[9]),
                "native_resolutions_minutes": sorted(
                    int(value) for value in str(row[10] or "").split(",") if value
                ),
            }
            for row in connection.execute(
                """
                SELECT country, service, market_stage, metric, direction, unit,
                       source, source_id, MIN(market_date), MAX(market_date),
                       GROUP_CONCAT(DISTINCT resolution_minutes)
                FROM balancing_market_data
                GROUP BY country, service, market_stage, metric, direction,
                         unit, source, source_id
                ORDER BY service, market_stage, metric, direction, source_id
                """
            ).fetchall()
        ],
    }


# ============================================================
# MAIN BUILD
# ============================================================

def build_public_database() -> None:

    print()
    print("=" * 72)
    print(
        "BUILD SANITIZED PUBLIC IBERIAN ENERGY DATABASE"
    )
    print("=" * 72)
    print()

    print(
        f"Source database: "
        f"{SOURCE_DATABASE_PATH}"
    )

    print(
        f"Public database: "
        f"{PUBLIC_DATABASE_PATH}"
    )

    print()


    # --------------------------------------------------------
    # CHECK LOCAL DATABASE
    # --------------------------------------------------------

    if not SOURCE_DATABASE_PATH.exists():

        raise FileNotFoundError(
            (
                "Source database not found: "
                f"{SOURCE_DATABASE_PATH}"
            )
        )


    # --------------------------------------------------------
    # CREATE DEPLOYMENT DIRECTORY
    # --------------------------------------------------------

    PUBLIC_DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    # --------------------------------------------------------
    # REMOVE PREVIOUS PUBLIC DB
    # --------------------------------------------------------

    if PUBLIC_DATABASE_PATH.exists():

        print(
            "Removing previous public database..."
        )

        PUBLIC_DATABASE_PATH.unlink()

        print()


    # ========================================================
    # OPEN DATABASES
    # ========================================================

    source_connection = sqlite3.connect(
        SOURCE_DATABASE_PATH
    )

    public_connection = sqlite3.connect(
        PUBLIC_DATABASE_PATH
    )

    try:

        # ----------------------------------------------------
        # REQUIRED SOURCE TABLES
        # ----------------------------------------------------

        required_source_tables = {
            "balancing_market_data",
            "omie_day_ahead_prices",
            "market_price_data",
            "market_events",
            "entsoe_generation_monthly",
            "entsoe_installed_capacity",
        }

        missing_tables = {
            table
            for table
            in required_source_tables
            if not table_exists(
                source_connection,
                table,
            )
        }

        if missing_tables:

            raise RuntimeError(
                (
                    "Local database is missing "
                    "required tables: "
                    + ", ".join(
                        sorted(
                            missing_tables
                        )
                    )
                )
            )


        # ====================================================
        # CREATE PUBLIC TABLE SCHEMAS
        #
        # We clone only explicitly approved table structures.
        # No source data are copied automatically.
        # ====================================================

        print(
            "Creating public table schemas..."
        )

        for table_name in [
            "balancing_market_data",
            "omie_day_ahead_prices",
            "market_price_data",
            "market_events",
            "entsoe_generation_monthly",
            "entsoe_installed_capacity",
        ]:

            public_connection.execute(
                get_table_sql(
                    source_connection,
                    table_name,
                )
            )

        public_connection.execute(
            """
            CREATE TABLE market_catalog_cache (
                id INTEGER PRIMARY KEY
                    CHECK (id = 1),

                payload_json TEXT NOT NULL,

                built_at_utc TEXT NOT NULL
            )
            """
        )

        public_connection.commit()

        print(
            "    Schemas created."
        )

        print()

        # ====================================================
        # ENTSO-E FUNDAMENTALS (SPAIN AND PORTUGAL)
        # ====================================================

        print("Copying ENTSO-E generation and installed capacity...")
        generation_count = copy_query_in_batches(
            source_connection, public_connection,
            """SELECT month, country, technology, generation_mwh,
                      observed_hours, expected_hours, source
               FROM entsoe_generation_monthly
               WHERE source = 'ENTSO-E' AND country IN ('ES', 'PT')
               ORDER BY month, country, technology""",
            """INSERT INTO entsoe_generation_monthly
               (month, country, technology, generation_mwh, observed_hours,
                expected_hours, source) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        )
        capacity_count = copy_query_in_batches(
            source_connection, public_connection,
            """SELECT year, country, technology, capacity_mw, source
               FROM entsoe_installed_capacity
               WHERE source = 'ENTSO-E' AND country IN ('ES', 'PT')
               ORDER BY year, country, technology""",
            """INSERT INTO entsoe_installed_capacity
               (year, country, technology, capacity_mw, source)
               VALUES (?, ?, ?, ?, ?)""",
        )
        public_connection.commit()
        print()


        # ====================================================
        # APPROVED BALANCING PRICES
        #
        # Only validated Spanish REE/ESIOS aFRR and mFRR are public.
        # ====================================================

        print("Copying approved Spanish ESIOS aFRR/mFRR prices...")
        balancing_count = copy_query_in_batches(
            source_connection, public_connection,
            """
            SELECT timestamp_utc, timestamp_market, market_date, period,
                   country, service, market_stage, metric, direction, value,
                   unit, resolution_minutes, source, source_id
            FROM balancing_market_data
            WHERE source = 'ESIOS' AND country = 'ES'
              AND service IN ('afrr', 'mfrr')
            ORDER BY timestamp_utc, service, market_stage, metric, direction,
                     source_id
            """,
            """
            INSERT INTO balancing_market_data (
                timestamp_utc, timestamp_market, market_date, period, country,
                service, market_stage, metric, direction, value, unit,
                resolution_minutes, source, source_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
        )
        public_connection.commit()


        # ====================================================
        # LEGACY DAY-AHEAD TABLE
        #
        # Retained for the existing /omie/* API endpoints.
        # ====================================================

        print(
            "Copying legacy OMIE day-ahead table..."
        )

        legacy_count = copy_query_in_batches(
            source_connection,
            public_connection,

            """
            SELECT
                timestamp_utc,
                timestamp_market,
                market_date,
                period,
                bidding_zone,
                price_eur_mwh

            FROM omie_day_ahead_prices

            ORDER BY
                timestamp_utc,
                bidding_zone
            """,

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
            """,
        )

        public_connection.commit()

        print()


        # ====================================================
        # UNIFIED MARKET PRICE DATA
        #
        # SECURITY POLICY:
        #
        #   source = OMIE
        #
        # and market must be one of:
        #
        #   day_ahead
        #   intraday_auction
        #   intraday_continuous
        #
        # No balancing rows are copied.
        # ====================================================

        print(
            "Copying sanitized unified OMIE market data..."
        )

        placeholders = ",".join(
            "?"
            for _ in PUBLIC_MARKETS
        )

        public_market_count = (
            copy_query_in_batches(

                source_connection,
                public_connection,

                f"""
                SELECT
                    timestamp_utc,
                    timestamp_market,
                    market_date,
                    period,
                    country,
                    market,
                    market_stage,
                    direction,
                    session,
                    price_value,
                    price_unit,
                    native_resolution_minutes,
                    source,
                    source_id

                FROM market_price_data

                WHERE source = 'OMIE'

                  AND market IN (
                      {placeholders}
                  )

                ORDER BY
                    timestamp_utc,
                    country,
                    market,
                    session
                """,

                """
                INSERT INTO market_price_data (
                    timestamp_utc,
                    timestamp_market,
                    market_date,
                    period,
                    country,
                    market,
                    market_stage,
                    direction,
                    session,
                    price_value,
                    price_unit,
                    native_resolution_minutes,
                    source,
                    source_id
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?
                )
                """,

                tuple(
                    sorted(
                        PUBLIC_MARKETS
                    )
                ),
            )
        )

        public_connection.commit()

        print()


        # ====================================================
        # WHOLESALE MARKET EVENTS ONLY
        # ====================================================

        print(
            "Copying wholesale market events..."
        )

        event_placeholders = ",".join(
            "?"
            for _ in PUBLIC_MARKETS
        )

        event_count = (
            copy_query_in_batches(

                source_connection,
                public_connection,

                f"""
                SELECT
                    event_date,
                    country,
                    service,
                    event_type,
                    title,
                    description,
                    source

                FROM market_events

                WHERE service IN (
                    {event_placeholders}
                )

                ORDER BY
                    event_date,
                    country,
                    service
                """,

                """
                INSERT INTO market_events (
                    event_date,
                    country,
                    service,
                    event_type,
                    title,
                    description,
                    source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,

                tuple(
                    sorted(
                        PUBLIC_MARKETS
                    )
                ),
            )
        )

        public_connection.commit()

        print()


        # ====================================================
        # RECREATE APPROVED INDEXES
        #
        # We create them only after bulk loading.
        # ====================================================

        print(
            "Creating public database indexes..."
        )

        for table_name in [
            "balancing_market_data",
            "omie_day_ahead_prices",
            "market_price_data",
            "market_events",
            "entsoe_generation_monthly",
            "entsoe_installed_capacity",
        ]:

            for index_sql in get_index_sql(
                source_connection,
                table_name,
            ):

                public_connection.execute(
                    index_sql
                )

        public_connection.commit()

        print(
            "    Indexes created."
        )

        print()


        # ====================================================
        # MATERIALISED PUBLIC CATALOG
        # ====================================================

        print(
            "Building approved public market catalog..."
        )

        catalog = build_public_catalog(
            public_connection
        )

        catalog_json = json.dumps(
            catalog,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        built_at_utc = (
            datetime.now(
                timezone.utc
            )
            .isoformat()
        )

        public_connection.execute(
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
            """,
            (
                catalog_json,
                built_at_utc,
            ),
        )

        public_connection.commit()

        catalog_rows = len(
            catalog["wholesale"]
        )

        print(
            f"    Wholesale catalog rows: "
            f"{catalog_rows}"
        )

        print(
            f"    Balancing catalog rows: "
            f"{len(catalog['balancing'])}"
        )

        print()


        # ====================================================
        # SECURITY VALIDATION
        # ====================================================

        print(
            "Running public database security checks..."
        )


        # ----------------------------------------------------
        # TABLE WHITELIST
        # ----------------------------------------------------

        public_tables = {
            row[0]
            for row
            in public_connection.execute(
                """
                SELECT name
                FROM sqlite_master

                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        }

        unexpected_tables = (
            public_tables
            - PUBLIC_TABLES
        )

        missing_public_tables = (
            PUBLIC_TABLES
            - public_tables
        )

        if unexpected_tables:

            raise RuntimeError(
                (
                    "SECURITY CHECK FAILED. "
                    "Unexpected public tables: "
                    + ", ".join(
                        sorted(
                            unexpected_tables
                        )
                    )
                )
            )

        if missing_public_tables:

            raise RuntimeError(
                (
                    "Public database is missing "
                    "required tables: "
                    + ", ".join(
                        sorted(
                            missing_public_tables
                        )
                    )
                )
            )


        # ----------------------------------------------------
        # ONLY OMIE SOURCE IN UNIFIED WHOLESALE TABLE
        # ----------------------------------------------------

        non_omie_rows = (
            public_connection.execute(
                """
                SELECT COUNT(*)

                FROM market_price_data

                WHERE source <> 'OMIE'
                   OR source IS NULL
                """
            ).fetchone()[0]
        )

        if non_omie_rows != 0:

            raise RuntimeError(
                (
                    "SECURITY CHECK FAILED. "
                    f"Found {non_omie_rows:,} "
                    "non-OMIE unified rows."
                )
            )


        # ----------------------------------------------------
        # ONLY APPROVED ESIOS / REN BALANCING ROWS
        # ----------------------------------------------------

        forbidden_balancing_rows = public_connection.execute(
            """
            SELECT COUNT(*) FROM balancing_market_data
            WHERE NOT (
                source = 'ESIOS' AND country = 'ES'
                AND service IN ('afrr', 'mfrr')
            )
            """
        ).fetchone()[0]

        if forbidden_balancing_rows != 0:

            raise RuntimeError(
                (
                    "SECURITY CHECK FAILED. "
                    f"Found "
                    f"{forbidden_balancing_rows:,} "
                    "unapproved balancing rows."
                )
            )


        # ----------------------------------------------------
        # CATALOG BALANCING SERIES MUST MATCH APPROVED SCOPE
        # ----------------------------------------------------

        cached_payload = (
            public_connection.execute(
                """
                SELECT payload_json
                FROM market_catalog_cache
                WHERE id = 1
                """
            ).fetchone()
        )

        if cached_payload is None:

            raise RuntimeError(
                "Public market catalog cache is missing."
            )

        cached_catalog = json.loads(
            cached_payload[0]
        )

        forbidden_catalog_rows = [
            row
            for row in cached_catalog.get(
                "balancing",
                [],
            )
            if (
                not (
                    row.get("source") == "ESIOS"
                    and row.get("country") == "ES"
                    and row.get("market") in {"afrr", "mfrr"}
                )
            )
        ]

        if forbidden_catalog_rows:

            raise RuntimeError(
                (
                    "SECURITY CHECK FAILED. "
                    "Public catalog contains "
                    "unapproved balancing entries."
                )
            )


        # ----------------------------------------------------
        # MARKET COUNTS
        # ----------------------------------------------------

        rows_by_market = (
            public_connection.execute(
                """
                SELECT
                    market,
                    COUNT(*)

                FROM market_price_data

                GROUP BY market

                ORDER BY market
                """
            ).fetchall()
        )


        # ----------------------------------------------------
        # SOURCE COUNTS
        # ----------------------------------------------------

        rows_by_source = (
            public_connection.execute(
                """
                SELECT
                    source,
                    COUNT(*)

                FROM market_price_data

                GROUP BY source

                ORDER BY source
                """
            ).fetchall()
        )


        # ----------------------------------------------------
        # SQLITE INTEGRITY
        # ----------------------------------------------------

        integrity = (
            public_connection.execute(
                """
                PRAGMA integrity_check
                """
            ).fetchone()[0]
        )

        if integrity != "ok":

            raise RuntimeError(
                (
                    "SQLite integrity check failed: "
                    f"{integrity}"
                )
            )


        print(
            "    Security checks passed."
        )

        print()


        # ====================================================
        # VACUUM
        # ====================================================

        print(
            "Compacting public database..."
        )

        public_connection.commit()

        public_connection.execute(
            "VACUUM"
        )

        print(
            "    VACUUM complete."
        )

        print()


    finally:

        source_connection.close()

        public_connection.close()


    # ========================================================
    # FINAL REPORT
    # ========================================================

    size_bytes = (
        PUBLIC_DATABASE_PATH
        .stat()
        .st_size
    )

    size_mb = (
        size_bytes
        / 1024
        / 1024
    )

    print("=" * 72)
    print(
        "PUBLIC DATABASE BUILD REPORT"
    )
    print("=" * 72)

    print()

    print(
        "Public tables:"
    )

    for table_name in sorted(
        PUBLIC_TABLES
    ):

        print(
            f"  {table_name}"
        )

    print()

    print(
        f"Legacy day-ahead rows: "
        f"{legacy_count:,}"
    )

    print(
        f"Unified OMIE rows: "
        f"{public_market_count:,}"
    )

    print(f"Approved Spanish ESIOS balancing rows: {balancing_count:,}")
    print(f"ENTSO-E monthly generation rows: {generation_count:,}")
    print(f"ENTSO-E installed-capacity rows: {capacity_count:,}")

    print(
        f"Wholesale event rows: "
        f"{event_count:,}"
    )

    print(
        f"Wholesale catalog rows: "
        f"{catalog_rows:,}"
    )

    print(
        f"Balancing catalog rows: "
        f"{len(catalog['balancing']):,}"
    )

    print()

    print(
        "Rows by unified market:"
    )

    for (
        market,
        count,
    ) in rows_by_market:

        print(
            f"  {market}: "
            f"{count:,}"
        )

    print()

    print(
        "Rows by source:"
    )

    for (
        source,
        count,
    ) in rows_by_source:

        print(
            f"  {source}: "
            f"{count:,}"
        )

    print()

    print(
        f"Database size: "
        f"{size_mb:.2f} MB"
    )

    print(
        "SQLite integrity check: OK"
    )

    print(
        "Non-OMIE unified rows: 0"
    )

    print(f"Approved Spanish ESIOS balancing rows: {balancing_count:,}")

    print(
        f"Balancing catalog rows: "
        f"{len(catalog['balancing']):,}"
    )

    print()

    print("=" * 72)
    print(
        "PUBLIC DATABASE BUILD PASSED"
    )
    print("=" * 72)

    print()

    print(
        f"Created at: "
        f"{PUBLIC_DATABASE_PATH}"
    )

    print()


# ============================================================
# COMMAND LINE
# ============================================================

if __name__ == "__main__":
    build_public_database()
