import sqlite3
from pathlib import Path


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


with sqlite3.connect(DATABASE_PATH) as connection:

    # --------------------------------------------------
    # QUERY 1: TOTAL LOAD OBSERVATIONS
    # --------------------------------------------------

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


    # --------------------------------------------------
    # QUERY 2: ROWS BY COUNTRY
    # --------------------------------------------------

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


    # --------------------------------------------------
    # QUERY 3: FIRST PORTUGUESE LOAD OBSERVATIONS
    # --------------------------------------------------

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


    # --------------------------------------------------
    # QUERY 4: JOIN OMIE PRICE + REN LOAD
    # --------------------------------------------------

    price_load = connection.execute(
        """
        SELECT
            p.timestamp_market,
            p.price_eur_mwh,
            l.load_mw

        FROM omie_day_ahead_prices AS p

        INNER JOIN electricity_load AS l
            ON p.timestamp_utc = l.timestamp_utc

        WHERE
            p.bidding_zone = 'PT'
            AND l.country = 'PT'
            AND p.market_date = '20260811'

        ORDER BY p.timestamp_utc;
        """
    ).fetchall()


    print()
    print(
        "Portuguese price + load:"
    )

    for row in price_load[:10]:
        print(row)


    print()
    print(
        f"Joined observations: "
        f"{len(price_load)}"
    )