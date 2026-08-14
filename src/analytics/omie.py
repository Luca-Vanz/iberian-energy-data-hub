import sqlite3
from pathlib import Path

import pandas as pd


DATABASE_PATH = Path("data") / "database" / "iberian_energy.db"


def get_daily_market_summary() -> pd.DataFrame:
    query = """
        WITH period_prices AS (
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

        FROM period_prices

        GROUP BY market_date

        ORDER BY market_date;
    """

    with sqlite3.connect(DATABASE_PATH) as connection:
        df = pd.read_sql_query(
            query,
            connection,
        )

    return df


if __name__ == "__main__":
    summary = get_daily_market_summary()
    print(summary)