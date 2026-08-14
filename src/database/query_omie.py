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


    # Query 4: daily average Spanish day-ahead price
    query = """
        SELECT
            market_date,
            ROUND(AVG(price_eur_mwh), 2) AS avg_price
        FROM omie_day_ahead_prices
        WHERE bidding_zone = 'ES'
        GROUP BY market_date
        ORDER BY market_date;
    """

    results = connection.execute(query).fetchall()

    print()
    print("Daily average Spanish price:")

    for row in results:
        print(row)

    # Query 5: daily ES-PT market summary
    query = """
        WITH hourly_prices AS (
            SELECT
                market_date,
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
                ) AS price_pt

            FROM omie_day_ahead_prices

            GROUP BY
                market_date,
                timestamp_market
        )

        SELECT
            market_date,

            ROUND(AVG(price_es), 2) AS avg_price_es,

            ROUND(AVG(price_pt), 2) AS avg_price_pt,

            SUM(
                CASE
                    WHEN ABS(price_pt - price_es) > 0.001
                    THEN 1
                    ELSE 0
                END
            ) AS split_periods,

            ROUND(
                MAX(ABS(price_pt - price_es)),
                2
            ) AS max_spread

        FROM hourly_prices

        GROUP BY market_date

        ORDER BY market_date;
    """

    results = connection.execute(query).fetchall()

    print()
    print("Daily ES-PT market summary:")

    for row in results:
        print(row)