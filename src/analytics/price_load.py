import sqlite3
from pathlib import Path

import pandas as pd


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


def get_price_load(
    country: str,
    date: str,
) -> pd.DataFrame:

    query = """
        SELECT
            p.timestamp_utc,
            p.timestamp_market,
            p.market_date,
            p.period,
            p.bidding_zone,
            p.price_eur_mwh,
            l.load_mw,
            l.source AS load_source

        FROM omie_day_ahead_prices AS p

        INNER JOIN electricity_load AS l
            ON p.timestamp_utc = l.timestamp_utc

        WHERE
            p.bidding_zone = ?
            AND l.country = ?
            AND p.market_date = ?

        ORDER BY p.timestamp_utc;
    """

def get_daily_price_load_summary(
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:

    query = """
        SELECT
            p.market_date,

            ROUND(
                AVG(p.price_eur_mwh),
                2
            ) AS avg_price_eur_mwh,

            ROUND(
                MIN(p.price_eur_mwh),
                2
            ) AS min_price_eur_mwh,

            ROUND(
                MAX(p.price_eur_mwh),
                2
            ) AS max_price_eur_mwh,

            ROUND(
                AVG(l.load_mw),
                2
            ) AS avg_load_mw,

            ROUND(
                MIN(l.load_mw),
                2
            ) AS min_load_mw,

            ROUND(
                MAX(l.load_mw),
                2
            ) AS max_load_mw

        FROM omie_day_ahead_prices AS p

        INNER JOIN electricity_load AS l
            ON p.timestamp_utc = l.timestamp_utc

        WHERE
            p.bidding_zone = 'PT'
            AND l.country = 'PT'
    """


    parameters = []


    if start_date is not None:

        query += """
            AND p.market_date >= ?
        """

        parameters.append(
            start_date
        )


    if end_date is not None:

        query += """
            AND p.market_date <= ?
        """

        parameters.append(
            end_date
        )


    query += """
        GROUP BY p.market_date

        ORDER BY p.market_date;
    """


    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:

        df = pd.read_sql_query(
            query,
            connection,
            params=parameters,
        )


    return df

    parameters = [
        country,
        country,
        date,
    ]


    with sqlite3.connect(DATABASE_PATH) as connection:

        df = pd.read_sql_query(
            query,
            connection,
            params=parameters,
        )


    return df


if __name__ == "__main__":

    result = get_price_load(
        country="PT",
        date="20260811",
    )

    print(
        result.head(10)
        .to_string(index=False)
    )

    print()

    print(
        f"Joined observations: "
        f"{len(result)}"
    )