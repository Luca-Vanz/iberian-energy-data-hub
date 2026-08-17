import sqlite3
from pathlib import Path


# ==================================================
# PATHS
# ==================================================

SOURCE_DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


PUBLIC_DATABASE_PATH = (
    Path("deployment")
    / "iberian_energy_public.db"
)


# ==================================================
# PUBLIC TABLE WHITELIST
# ==================================================

PUBLIC_TABLES = {
    "omie_day_ahead_prices",
}


# ==================================================
# CREATE PUBLIC DATABASE
# ==================================================

def build_public_database():

    print("=" * 60)
    print("BUILD PUBLIC IBERIAN ENERGY DATABASE")
    print("=" * 60)

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


    # --------------------------------------------------
    # CHECK SOURCE DATABASE EXISTS
    # --------------------------------------------------

    if not SOURCE_DATABASE_PATH.exists():

        raise FileNotFoundError(
            f"Source database not found: "
            f"{SOURCE_DATABASE_PATH}"
        )


    # --------------------------------------------------
    # CREATE DEPLOYMENT FOLDER
    # --------------------------------------------------

    PUBLIC_DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    # --------------------------------------------------
    # DELETE OLD PUBLIC DATABASE
    # --------------------------------------------------

    if PUBLIC_DATABASE_PATH.exists():

        print(
            "Existing public database found."
        )

        print(
            "Deleting it before rebuilding..."
        )

        PUBLIC_DATABASE_PATH.unlink()

        print()


    # ==================================================
    # READ SOURCE DATABASE
    # ==================================================

    with sqlite3.connect(
        SOURCE_DATABASE_PATH
    ) as source_connection:

        # ----------------------------------------------
        # SHOW SOURCE TABLES
        # ----------------------------------------------

        source_tables = (
            source_connection.execute(
                """
                SELECT name

                FROM sqlite_master

                WHERE type = 'table'

                ORDER BY name;
                """
            ).fetchall()
        )


        source_tables = [
            row[0]
            for row in source_tables
        ]


        print(
            "Tables in LOCAL database:"
        )


        for table in source_tables:

            print(
                f"  {table}"
            )


        print()


        # ----------------------------------------------
        # ENSURE OMIE TABLE EXISTS
        # ----------------------------------------------

        if (
            "omie_day_ahead_prices"
            not in source_tables
        ):

            raise RuntimeError(
                "Required source table "
                "'omie_day_ahead_prices' "
                "does not exist."
            )


        # ----------------------------------------------
        # CHECK REQUIRED OMIE COLUMNS
        # ----------------------------------------------

        source_columns = (
            source_connection.execute(
                """
                PRAGMA table_info(
                    omie_day_ahead_prices
                );
                """
            ).fetchall()
        )


        source_column_names = {
            row[1]
            for row in source_columns
        }


        required_columns = {
            "timestamp_utc",
            "timestamp_market",
            "market_date",
            "period",
            "bidding_zone",
            "price_eur_mwh",
        }


        missing_columns = (
            required_columns
            - source_column_names
        )


        if missing_columns:

            raise RuntimeError(
                "OMIE table is missing required "
                "columns: "
                + ", ".join(
                    sorted(
                        missing_columns
                    )
                )
            )


        # ----------------------------------------------
        # SOURCE ROW COUNT
        # ----------------------------------------------

        source_row_count = (
            source_connection.execute(
                """
                SELECT COUNT(*)

                FROM omie_day_ahead_prices;
                """
            ).fetchone()[0]
        )


        source_market_days = (
            source_connection.execute(
                """
                SELECT COUNT(
                    DISTINCT market_date
                )

                FROM omie_day_ahead_prices;
                """
            ).fetchone()[0]
        )


        source_first_date, source_last_date = (
            source_connection.execute(
                """
                SELECT
                    MIN(market_date),
                    MAX(market_date)

                FROM omie_day_ahead_prices;
                """
            ).fetchone()
        )


        source_zone_counts = (
            source_connection.execute(
                """
                SELECT
                    bidding_zone,
                    COUNT(*)

                FROM omie_day_ahead_prices

                GROUP BY bidding_zone

                ORDER BY bidding_zone;
                """
            ).fetchall()
        )


        # ----------------------------------------------
        # VALIDATE BIDDING ZONES
        # ----------------------------------------------

        source_zones = {
            row[0]
            for row in source_zone_counts
        }


        unexpected_zones = (
            source_zones
            - {"ES", "PT"}
        )


        if unexpected_zones:

            raise RuntimeError(
                "Unexpected bidding zones found "
                "in OMIE table: "
                + ", ".join(
                    sorted(
                        unexpected_zones
                    )
                )
            )


        # ----------------------------------------------
        # CHECK NULL VALUES
        # ----------------------------------------------

        source_null_rows = (
            source_connection.execute(
                """
                SELECT COUNT(*)

                FROM omie_day_ahead_prices

                WHERE
                    timestamp_utc IS NULL
                    OR timestamp_market IS NULL
                    OR market_date IS NULL
                    OR period IS NULL
                    OR bidding_zone IS NULL
                    OR price_eur_mwh IS NULL;
                """
            ).fetchone()[0]
        )


        if source_null_rows > 0:

            raise RuntimeError(
                f"Source OMIE table contains "
                f"{source_null_rows} rows "
                f"with null values."
            )


        print(
            "Source OMIE data:"
        )

        print(
            f"  Rows: "
            f"{source_row_count}"
        )

        print(
            f"  Market days: "
            f"{source_market_days}"
        )

        print(
            f"  First date: "
            f"{source_first_date}"
        )

        print(
            f"  Last date: "
            f"{source_last_date}"
        )


        print(
            "  Rows by bidding zone:"
        )


        for (
            zone,
            count,
        ) in source_zone_counts:

            print(
                f"    {zone}: "
                f"{count}"
            )


        print()


        # ----------------------------------------------
        # READ ONLY WHITELISTED OMIE DATA
        # ----------------------------------------------

        omie_rows = (
            source_connection.execute(
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
                    bidding_zone;
                """
            ).fetchall()
        )


    # ==================================================
    # CREATE COMPLETELY NEW PUBLIC DATABASE
    # ==================================================

    with sqlite3.connect(
        PUBLIC_DATABASE_PATH
    ) as public_connection:

        # ----------------------------------------------
        # CREATE OMIE TABLE EXPLICITLY
        # ----------------------------------------------

        public_connection.execute(
            """
            CREATE TABLE omie_day_ahead_prices (

                timestamp_utc TEXT NOT NULL,

                timestamp_market TEXT NOT NULL,

                market_date TEXT NOT NULL,

                period INTEGER NOT NULL,

                bidding_zone TEXT NOT NULL,

                price_eur_mwh REAL NOT NULL,

                PRIMARY KEY (
                    timestamp_utc,
                    bidding_zone
                )
            );
            """
        )


        # ----------------------------------------------
        # INSERT OMIE DATA
        # ----------------------------------------------

        public_connection.executemany(
            """
            INSERT INTO omie_day_ahead_prices (

                timestamp_utc,
                timestamp_market,
                market_date,
                period,
                bidding_zone,
                price_eur_mwh
            )

            VALUES (
                ?, ?, ?, ?, ?, ?
            );
            """,
            omie_rows,
        )


        public_connection.commit()


        # ==================================================
        # PUBLIC DATABASE VALIDATION
        # ==================================================

        public_tables = (
            public_connection.execute(
                """
                SELECT name

                FROM sqlite_master

                WHERE type = 'table'

                ORDER BY name;
                """
            ).fetchall()
        )


        public_tables = {
            row[0]
            for row in public_tables
        }


        # ----------------------------------------------
        # SECURITY CHECK:
        # ONLY WHITELISTED TABLES MAY EXIST
        # ----------------------------------------------

        unexpected_public_tables = (
            public_tables
            - PUBLIC_TABLES
        )


        missing_public_tables = (
            PUBLIC_TABLES
            - public_tables
        )


        if unexpected_public_tables:

            raise RuntimeError(
                "SECURITY CHECK FAILED. "
                "Unexpected tables found in "
                "public database: "
                + ", ".join(
                    sorted(
                        unexpected_public_tables
                    )
                )
            )


        if missing_public_tables:

            raise RuntimeError(
                "Public database is missing "
                "required tables: "
                + ", ".join(
                    sorted(
                        missing_public_tables
                    )
                )
            )


        # ----------------------------------------------
        # EXPLICIT REN TABLE CHECK
        # ----------------------------------------------

        forbidden_tables = {
            "electricity_load",
            "electricity_generation",
        }


        leaked_tables = (
            public_tables
            & forbidden_tables
        )


        if leaked_tables:

            raise RuntimeError(
                "SECURITY CHECK FAILED. "
                "REN-derived tables detected: "
                + ", ".join(
                    sorted(
                        leaked_tables
                    )
                )
            )


        # ----------------------------------------------
        # ROW COUNT CHECK
        # ----------------------------------------------

        public_row_count = (
            public_connection.execute(
                """
                SELECT COUNT(*)

                FROM omie_day_ahead_prices;
                """
            ).fetchone()[0]
        )


        if (
            public_row_count
            != source_row_count
        ):

            raise RuntimeError(
                "Row-count validation failed. "
                f"Source has "
                f"{source_row_count} rows "
                f"but public database has "
                f"{public_row_count}."
            )


        # ----------------------------------------------
        # PUBLIC DATE RANGE
        # ----------------------------------------------

        public_market_days = (
            public_connection.execute(
                """
                SELECT COUNT(
                    DISTINCT market_date
                )

                FROM omie_day_ahead_prices;
                """
            ).fetchone()[0]
        )


        public_first_date, public_last_date = (
            public_connection.execute(
                """
                SELECT
                    MIN(market_date),
                    MAX(market_date)

                FROM omie_day_ahead_prices;
                """
            ).fetchone()
        )


        public_zone_counts = (
            public_connection.execute(
                """
                SELECT
                    bidding_zone,
                    COUNT(*)

                FROM omie_day_ahead_prices

                GROUP BY bidding_zone

                ORDER BY bidding_zone;
                """
            ).fetchall()
        )


        # ----------------------------------------------
        # SQLITE INTEGRITY CHECK
        # ----------------------------------------------

        integrity_result = (
            public_connection.execute(
                """
                PRAGMA integrity_check;
                """
            ).fetchone()[0]
        )


        if integrity_result != "ok":

            raise RuntimeError(
                "SQLite integrity check failed: "
                f"{integrity_result}"
            )


        # ----------------------------------------------
        # COMPACT DATABASE
        # ----------------------------------------------

        public_connection.execute(
            "VACUUM;"
        )


    # ==================================================
    # FINAL REPORT
    # ==================================================

    database_size_mb = (
        PUBLIC_DATABASE_PATH
        .stat()
        .st_size
        / (1024 * 1024)
    )


    print("=" * 60)

    print(
        "PUBLIC DATABASE VALIDATION"
    )

    print("=" * 60)


    print(
        "Tables in PUBLIC database:"
    )


    for table in sorted(
        public_tables
    ):

        print(
            f"  {table}"
        )


    print()


    print(
        f"Total rows: "
        f"{public_row_count}"
    )

    print(
        f"Market days: "
        f"{public_market_days}"
    )

    print(
        f"First date: "
        f"{public_first_date}"
    )

    print(
        f"Last date: "
        f"{public_last_date}"
    )


    print()

    print(
        "Rows by bidding zone:"
    )


    for (
        zone,
        count,
    ) in public_zone_counts:

        print(
            f"  {zone}: "
            f"{count}"
        )


    print()

    print(
        f"Database size: "
        f"{database_size_mb:.2f} MB"
    )


    print()

    print(
        "REN electricity_load table: "
        "NOT PRESENT"
    )

    print(
        "REN electricity_generation table: "
        "NOT PRESENT"
    )


    print()

    print(
        "SQLite integrity check: OK"
    )


    print()

    print("=" * 60)

    print(
        "PUBLIC DATABASE BUILD PASSED"
    )

    print("=" * 60)


    print()

    print(
        f"Safe public database created at:"
    )

    print(
        PUBLIC_DATABASE_PATH
    )


# ==================================================
# COMMAND LINE
# ==================================================

if __name__ == "__main__":

    build_public_database()