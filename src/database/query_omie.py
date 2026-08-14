import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data") / "database" / "iberian_energy.db"


with sqlite3.connect(DATABASE_PATH) as connection:

    # Query 1: count all rows
    query = """
        SELECT COUNT(*)
        FROM omie_day_ahead_prices;
    """

    result = connection.execute(query).fetchone()

    print("Number of rows:", result[0])

    # Query 2: average price by bidding zone
    query = """
        SELECT
            bidding_zone,
            AVG(price_eur_mwh)
        FROM omie_day_ahead_prices
        GROUP BY bidding_zone;
    """

    results = connection.execute(query).fetchall()

    print()
    print("Average price by bidding zone:")

    for row in results:
        print(row)


    # Query 3: periods with ES-PT price separation
    query = """
        SELECT
            timestamp_market,

            MAX(
                CASE
                    WHEN bidding_zone = 'ES'
                    THEN price_eur_mwh
                END
            ) AS price_es,

            MAX(
                CASE
                    WHEN bidding_zone = 'PT'
                    THEN price_eur_mwh
                END
            ) AS price_pt,

            ROUND(
                MAX(
                    CASE
                        WHEN bidding_zone = 'PT'
                        THEN price_eur_mwh
                    END
                )
                -
                MAX(
                    CASE
                        WHEN bidding_zone = 'ES'
                        THEN price_eur_mwh
                    END
                ),
                2
            ) AS pt_minus_es

        FROM omie_day_ahead_prices

        GROUP BY timestamp_market

        HAVING ABS(pt_minus_es) > 0.001

        ORDER BY timestamp_market;
    """

    results = connection.execute(query).fetchall()

    print()
    print("Periods with ES-PT price separation:")

    for row in results:
        print(row)