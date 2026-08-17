import sqlite3
from pathlib import Path


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


with sqlite3.connect(
    DATABASE_PATH
) as connection:

    # ==================================================
    # TOTAL ROWS
    # ==================================================

    total_rows = connection.execute(
        """
        SELECT COUNT(*)

        FROM electricity_generation;
        """
    ).fetchone()[0]


    print(
        f"Total generation rows: "
        f"{total_rows}"
    )


    # ==================================================
    # ROWS BY COUNTRY
    # ==================================================

    country_counts = (
        connection.execute(
            """
            SELECT
                country,
                COUNT(*)

            FROM electricity_generation

            GROUP BY country

            ORDER BY country;
            """
        ).fetchall()
    )


    print()
    print(
        "Rows by country:"
    )


    for row in country_counts:

        print(
            row
        )


    # ==================================================
    # ROWS BY TECHNOLOGY
    # ==================================================

    technology_counts = (
        connection.execute(
            """
            SELECT
                technology,
                COUNT(*)

            FROM electricity_generation

            WHERE country = 'PT'

            GROUP BY technology

            ORDER BY technology;
            """
        ).fetchall()
    )


    print()
    print(
        "Rows by technology:"
    )


    for row in technology_counts:

        print(
            row
        )


    # ==================================================
    # DAILY GENERATION STATISTICS
    # ==================================================

    technology_stats = (
        connection.execute(
            """
            SELECT
                technology,

                ROUND(
                    AVG(generation_mw),
                    2
                ) AS average_mw,

                ROUND(
                    MIN(generation_mw),
                    2
                ) AS minimum_mw,

                ROUND(
                    MAX(generation_mw),
                    2
                ) AS maximum_mw

            FROM electricity_generation

            WHERE
                country = 'PT'
                AND market_date = '20260811'

            GROUP BY technology

            ORDER BY technology;
            """
        ).fetchall()
    )


    print()
    print(
        "2026-08-11 generation statistics:"
    )


    for row in technology_stats:

        print(
            row
        )


    # ==================================================
    # FIRST PERIOD GENERATION MIX
    # ==================================================

    first_period = (
        connection.execute(
            """
            SELECT
                timestamp_market,
                technology,
                generation_mw

            FROM electricity_generation

            WHERE
                country = 'PT'
                AND market_date = '20260811'
                AND period = 1

            ORDER BY technology;
            """
        ).fetchall()
    )


    print()
    print(
        "Generation mix for period 1:"
    )


    for row in first_period:

        print(
            row
        )