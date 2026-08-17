import pandas as pd

from src.database.connection import (
    get_database_connection,
)


# ==================================================
# DAILY MARKET SUMMARY
# ==================================================

def get_daily_market_summary(
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:

    query = """
        WITH period_prices AS (

            SELECT
                timestamp_utc,
                market_date,

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
                timestamp_utc,
                market_date
        )

        SELECT
            market_date,

            ROUND(
                AVG(price_es),
                2
            ) AS avg_price_es,

            ROUND(
                AVG(price_pt),
                2
            ) AS avg_price_pt,

            SUM(
                CASE
                    WHEN ABS(
                        price_pt - price_es
                    ) > 0.001
                    THEN 1
                    ELSE 0
                END
            ) AS split_periods,

            ROUND(
                MAX(
                    ABS(
                        price_pt - price_es
                    )
                ),
                2
            ) AS max_spread

        FROM period_prices

        WHERE 1 = 1
    """


    parameters = []


    if start_date is not None:

        query += """
            AND market_date >= ?
        """

        parameters.append(
            start_date
        )


    if end_date is not None:

        query += """
            AND market_date <= ?
        """

        parameters.append(
            end_date
        )


    query += """
        GROUP BY market_date

        ORDER BY market_date;
    """


    with get_database_connection() as connection:

        df = pd.read_sql_query(
            query,
            connection,
            params=parameters,
        )


    return df


# ==================================================
# PRICE OBSERVATIONS BY BIDDING ZONE
# ==================================================

def get_prices(
    zone: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:

    query = """
        SELECT
            timestamp_utc,
            timestamp_market,
            market_date,
            period,
            bidding_zone,
            price_eur_mwh

        FROM omie_day_ahead_prices

        WHERE bidding_zone = ?
    """


    parameters = [
        zone
    ]


    if start_date is not None:

        query += """
            AND market_date >= ?
        """

        parameters.append(
            start_date
        )


    if end_date is not None:

        query += """
            AND market_date <= ?
        """

        parameters.append(
            end_date
        )


    query += """
        ORDER BY timestamp_utc;
    """


    with get_database_connection() as connection:

        df = pd.read_sql_query(
            query,
            connection,
            params=parameters,
        )


    return df


# ==================================================
# INTRADAY ES / PT PRICE COMPARISON
# ==================================================

def get_intraday_prices(
    date: str,
) -> pd.DataFrame:

    query = """
        WITH period_prices AS (

            SELECT
                timestamp_utc,
                timestamp_market,
                market_date,
                period,

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

            WHERE market_date = ?

            GROUP BY
                timestamp_utc,
                timestamp_market,
                market_date,
                period
        )

        SELECT
            timestamp_utc,
            timestamp_market,
            market_date,
            period,
            price_es,
            price_pt,

            ROUND(
                price_pt - price_es,
                2
            ) AS pt_minus_es

        FROM period_prices

        ORDER BY timestamp_utc;
    """


    with get_database_connection() as connection:

        df = pd.read_sql_query(
            query,
            connection,
            params=[
                date
            ],
        )


    return df


# ==================================================
# QUICK LOCAL TEST
# ==================================================

if __name__ == "__main__":

    print(
        "Daily market summary:"
    )

    daily_summary = (
        get_daily_market_summary()
    )

    print(
        daily_summary.head()
        .to_string(
            index=False
        )
    )


    print()
    print(
        f"Market days: "
        f"{len(daily_summary)}"
    )


    print()
    print(
        "Example intraday data:"
    )

    intraday = (
        get_intraday_prices(
            "20260811"
        )
    )

    print(
        intraday.head()
        .to_string(
            index=False
        )
    )