import sqlite3
from pathlib import Path


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


with sqlite3.connect(DATABASE_PATH) as connection:

    # Total electricity load observations
    total_rows = connection.execute(
        """
        SELECT COUNT(*)
        FROM electricity_load;
        """
    ).fetchone()[0]


    print(
        f"Total electricity load rows: "
        f"{total_rows}"
    )


    # Rows by country
    country_counts = connection.execute(
        """
        SELECT
            country,
            COUNT(*)

        FROM electricity_load

        GROUP BY country

        ORDER BY country;
        """
    ).fetchall()


    print()
    print("Rows by country:")

    for row in country_counts:
        print(row)


    # First five Portuguese observations
    first_rows = connection.execute(
        """
        SELECT
            timestamp_market,
            country,
            load_mw

        FROM electricity_load

        WHERE country = 'PT'

        ORDER BY timestamp_utc

        LIMIT 5;
        """
    ).fetchall()


    print()
    print(
        "First Portuguese load observations:"
    )

    for row in first_rows:
        print(row)