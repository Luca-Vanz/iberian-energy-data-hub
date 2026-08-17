import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


START_DATE = "20251001"
END_DATE = "20260814"


# --------------------------------------------------
# EXPECTED NUMBER OF 15-MINUTE PERIODS
# --------------------------------------------------

def expected_periods_for_date(
    market_date: str,
) -> int:

    date = pd.to_datetime(
        market_date,
        format="%Y%m%d",
    )

    next_date = (
        date
        + pd.Timedelta(days=1)
    )

    timestamps = pd.date_range(
        start=date,
        end=next_date,
        freq="15min",
        inclusive="left",
        tz="Europe/Madrid",
    )

    return len(timestamps)


# --------------------------------------------------
# EXPECTED CALENDAR DATES
# --------------------------------------------------

def generate_dates(
    start_date: str,
    end_date: str,
) -> list[str]:

    current_date = datetime.strptime(
        start_date,
        "%Y%m%d",
    )

    final_date = datetime.strptime(
        end_date,
        "%Y%m%d",
    )

    dates = []

    while current_date <= final_date:

        dates.append(
            current_date.strftime(
                "%Y%m%d"
            )
        )

        current_date += timedelta(
            days=1
        )

    return dates


# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

def validate_join():

    if not DATABASE_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: "
            f"{DATABASE_PATH}"
        )


    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:

        # ------------------------------------------
        # OMIE PORTUGUESE PRICE ROWS
        # ------------------------------------------

        price_rows = connection.execute(
            """
            SELECT COUNT(*)

            FROM omie_day_ahead_prices

            WHERE
                bidding_zone = 'PT'
                AND market_date
                    BETWEEN ? AND ?;
            """,
            (
                START_DATE,
                END_DATE,
            ),
        ).fetchone()[0]


        # ------------------------------------------
        # REN PORTUGUESE LOAD ROWS
        # ------------------------------------------

        load_rows = connection.execute(
            """
            SELECT COUNT(*)

            FROM electricity_load

            WHERE
                country = 'PT'
                AND market_date
                    BETWEEN ? AND ?;
            """,
            (
                START_DATE,
                END_DATE,
            ),
        ).fetchone()[0]


        # ------------------------------------------
        # INNER JOIN
        # ------------------------------------------

        joined_rows = connection.execute(
            """
            SELECT COUNT(*)

            FROM omie_day_ahead_prices AS p

            INNER JOIN electricity_load AS l
                ON p.timestamp_utc
                    = l.timestamp_utc

            WHERE
                p.bidding_zone = 'PT'
                AND l.country = 'PT'
                AND p.market_date
                    BETWEEN ? AND ?
                AND l.market_date
                    BETWEEN ? AND ?;
            """,
            (
                START_DATE,
                END_DATE,
                START_DATE,
                END_DATE,
            ),
        ).fetchone()[0]


        # ------------------------------------------
        # OMIE PRICES WITHOUT REN LOAD
        # ------------------------------------------

        prices_without_load = (
            connection.execute(
                """
                SELECT
                    p.timestamp_utc,
                    p.market_date,
                    p.period

                FROM omie_day_ahead_prices AS p

                LEFT JOIN electricity_load AS l
                    ON p.timestamp_utc
                        = l.timestamp_utc
                    AND l.country = 'PT'

                WHERE
                    p.bidding_zone = 'PT'
                    AND p.market_date
                        BETWEEN ? AND ?
                    AND l.timestamp_utc IS NULL

                ORDER BY p.timestamp_utc;
                """,
                (
                    START_DATE,
                    END_DATE,
                ),
            ).fetchall()
        )


        # ------------------------------------------
        # REN LOAD WITHOUT OMIE PRICE
        # ------------------------------------------

        load_without_price = (
            connection.execute(
                """
                SELECT
                    l.timestamp_utc,
                    l.market_date,
                    l.period

                FROM electricity_load AS l

                LEFT JOIN omie_day_ahead_prices AS p
                    ON l.timestamp_utc
                        = p.timestamp_utc
                    AND p.bidding_zone = 'PT'

                WHERE
                    l.country = 'PT'
                    AND l.market_date
                        BETWEEN ? AND ?
                    AND p.timestamp_utc IS NULL

                ORDER BY l.timestamp_utc;
                """,
                (
                    START_DATE,
                    END_DATE,
                ),
            ).fetchall()
        )


        # ------------------------------------------
        # MARKET DATE MISMATCHES
        # ------------------------------------------

        date_mismatches = (
            connection.execute(
                """
                SELECT
                    p.timestamp_utc,
                    p.market_date,
                    l.market_date

                FROM omie_day_ahead_prices AS p

                INNER JOIN electricity_load AS l
                    ON p.timestamp_utc
                        = l.timestamp_utc

                WHERE
                    p.bidding_zone = 'PT'
                    AND l.country = 'PT'
                    AND p.market_date
                        BETWEEN ? AND ?
                    AND p.market_date
                        != l.market_date

                ORDER BY p.timestamp_utc;
                """,
                (
                    START_DATE,
                    END_DATE,
                ),
            ).fetchall()
        )


        # ------------------------------------------
        # PERIOD NUMBER MISMATCHES
        # ------------------------------------------

        period_mismatches = (
            connection.execute(
                """
                SELECT
                    p.timestamp_utc,
                    p.market_date,
                    p.period,
                    l.period

                FROM omie_day_ahead_prices AS p

                INNER JOIN electricity_load AS l
                    ON p.timestamp_utc
                        = l.timestamp_utc

                WHERE
                    p.bidding_zone = 'PT'
                    AND l.country = 'PT'
                    AND p.market_date
                        BETWEEN ? AND ?
                    AND p.period
                        != l.period

                ORDER BY p.timestamp_utc;
                """,
                (
                    START_DATE,
                    END_DATE,
                ),
            ).fetchall()
        )


        # ------------------------------------------
        # JOINED ROWS PER MARKET DAY
        # ------------------------------------------

        daily_join_counts = (
            connection.execute(
                """
                SELECT
                    p.market_date,
                    COUNT(*)

                FROM omie_day_ahead_prices AS p

                INNER JOIN electricity_load AS l
                    ON p.timestamp_utc
                        = l.timestamp_utc

                WHERE
                    p.bidding_zone = 'PT'
                    AND l.country = 'PT'
                    AND p.market_date
                        BETWEEN ? AND ?

                GROUP BY p.market_date

                ORDER BY p.market_date;
                """,
                (
                    START_DATE,
                    END_DATE,
                ),
            ).fetchall()
        )


    # ==================================================
    # DAILY COMPLETENESS
    # ==================================================

    joined_dates = {
        str(market_date)
        for market_date, _
        in daily_join_counts
    }


    expected_dates = set(
        generate_dates(
            START_DATE,
            END_DATE,
        )
    )


    missing_join_dates = sorted(
        expected_dates
        - joined_dates
    )


    unexpected_daily_counts = []


    for (
        market_date,
        row_count,
    ) in daily_join_counts:

        market_date = str(
            market_date
        )

        expected_count = (
            expected_periods_for_date(
                market_date
            )
        )


        if row_count != expected_count:

            unexpected_daily_counts.append(
                (
                    market_date,
                    row_count,
                    expected_count,
                )
            )


    # ==================================================
    # REPORT
    # ==================================================

    print("=" * 60)
    print(
        "OMIE + REN PRICE/LOAD JOIN VALIDATION"
    )
    print("=" * 60)


    print(
        f"Validation range: "
        f"{START_DATE} to {END_DATE}"
    )

    print()

    print(
        f"OMIE PT price rows: "
        f"{price_rows}"
    )

    print(
        f"REN PT load rows: "
        f"{load_rows}"
    )

    print(
        f"Joined rows: "
        f"{joined_rows}"
    )


    print()

    print(
        f"OMIE prices without REN load: "
        f"{len(prices_without_load)}"
    )

    print(
        f"REN load rows without OMIE price: "
        f"{len(load_without_price)}"
    )

    print(
        f"Market-date mismatches: "
        f"{len(date_mismatches)}"
    )

    print(
        f"Period-number mismatches: "
        f"{len(period_mismatches)}"
    )


    print()

    print(
        "Missing joined market dates:"
    )


    if missing_join_dates:

        for date in missing_join_dates:

            print(
                f"  {date}"
            )

    else:

        print(
            "  None"
        )


    print()

    print(
        "Days with unexpected "
        "joined row count:"
    )


    if unexpected_daily_counts:

        for (
            market_date,
            actual,
            expected,
        ) in unexpected_daily_counts:

            print(
                f"  {market_date}: "
                f"{actual} rows "
                f"(expected {expected})"
            )

    else:

        print(
            "  None"
        )


    # ==================================================
    # FINAL VALIDATION
    # ==================================================

    validation_passed = (
        price_rows == load_rows
        and price_rows == joined_rows
        and len(prices_without_load) == 0
        and len(load_without_price) == 0
        and len(date_mismatches) == 0
        and len(period_mismatches) == 0
        and len(missing_join_dates) == 0
        and len(unexpected_daily_counts) == 0
    )


    print()
    print("=" * 60)


    if validation_passed:

        print(
            "VALIDATION PASSED"
        )

    else:

        print(
            "VALIDATION FAILED"
        )


    print("=" * 60)


if __name__ == "__main__":

    validate_join()