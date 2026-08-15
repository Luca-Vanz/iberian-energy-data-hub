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