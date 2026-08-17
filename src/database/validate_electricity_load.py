import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


# --------------------------------------------------
# GENERATE ALL CALENDAR DATES BETWEEN TWO DATES
# --------------------------------------------------

def generate_expected_dates(
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
# VALIDATE DATABASE
# --------------------------------------------------

def validate_database():

    if not DATABASE_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: "
            f"{DATABASE_PATH}"
        )


    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:

        # ------------------------------------------
        # BASIC DATABASE INFORMATION
        # ------------------------------------------

        total_rows = connection.execute(
            """
            SELECT COUNT(*)

            FROM electricity_load

            WHERE country = 'PT';
            """
        ).fetchone()[0]


        total_days = connection.execute(
            """
            SELECT COUNT(
                DISTINCT market_date
            )

            FROM electricity_load

            WHERE country = 'PT';
            """
        ).fetchone()[0]


        first_date, last_date = (
            connection.execute(
                """
                SELECT
                    MIN(market_date),
                    MAX(market_date)

                FROM electricity_load

                WHERE country = 'PT';
                """
            ).fetchone()
        )


        if (
            first_date is None
            or last_date is None
        ):

            raise ValueError(
                "No Portuguese electricity "
                "load data found."
            )


        # ------------------------------------------
        # DATES PRESENT IN DATABASE
        # ------------------------------------------

        database_dates = (
            connection.execute(
                """
                SELECT DISTINCT
                    market_date

                FROM electricity_load

                WHERE country = 'PT'

                ORDER BY market_date;
                """
            ).fetchall()
        )


        database_dates = {
            str(row[0])
            for row in database_dates
        }


        # ------------------------------------------
        # ROW COUNT PER DAY
        # ------------------------------------------

        daily_counts = (
            connection.execute(
                """
                SELECT
                    market_date,
                    COUNT(*) AS row_count

                FROM electricity_load

                WHERE country = 'PT'

                GROUP BY market_date

                ORDER BY market_date;
                """
            ).fetchall()
        )


        # ------------------------------------------
        # NULL VALUES
        # ------------------------------------------

        null_rows = connection.execute(
            """
            SELECT COUNT(*)

            FROM electricity_load

            WHERE
                country = 'PT'

                AND (
                    timestamp_utc IS NULL
                    OR timestamp_market IS NULL
                    OR market_date IS NULL
                    OR period IS NULL
                    OR load_mw IS NULL
                    OR source IS NULL
                    OR interval_minutes IS NULL
                );
            """
        ).fetchone()[0]


        # ------------------------------------------
        # DUPLICATES
        # ------------------------------------------

        duplicate_rows = (
            connection.execute(
                """
                SELECT
                    timestamp_utc,
                    country,
                    COUNT(*)

                FROM electricity_load

                WHERE country = 'PT'

                GROUP BY
                    timestamp_utc,
                    country

                HAVING COUNT(*) > 1;
                """
            ).fetchall()
        )


        # ------------------------------------------
        # SOURCE AND INTERVAL
        # ------------------------------------------

        source_counts = (
            connection.execute(
                """
                SELECT
                    source,
                    interval_minutes,
                    COUNT(*)

                FROM electricity_load

                WHERE country = 'PT'

                GROUP BY
                    source,
                    interval_minutes

                ORDER BY
                    source,
                    interval_minutes;
                """
            ).fetchall()
        )


        # ------------------------------------------
        # PERIOD RANGE PER DAY
        # ------------------------------------------

        period_ranges = (
            connection.execute(
                """
                SELECT
                    market_date,
                    MIN(period),
                    MAX(period),
                    COUNT(
                        DISTINCT period
                    )

                FROM electricity_load

                WHERE country = 'PT'

                GROUP BY market_date

                ORDER BY market_date;
                """
            ).fetchall()
        )


        # ------------------------------------------
        # LOAD VALUE RANGE
        # ------------------------------------------

        minimum_load, maximum_load = (
            connection.execute(
                """
                SELECT
                    MIN(load_mw),
                    MAX(load_mw)

                FROM electricity_load

                WHERE country = 'PT';
                """
            ).fetchone()
        )


    # ==================================================
    # CALENDAR COMPLETENESS
    # ==================================================

    expected_dates = set(
        generate_expected_dates(
            str(first_date),
            str(last_date),
        )
    )


    missing_dates = sorted(
        expected_dates
        - database_dates
    )


    # ==================================================
    # DST-AWARE DAILY ROW COUNTS
    # ==================================================

    unexpected_days = []


    for (
        market_date,
        row_count,
    ) in daily_counts:

        market_date = str(
            market_date
        )

        expected_count = (
            expected_periods_for_date(
                market_date
            )
        )


        if row_count != expected_count:

            unexpected_days.append(
                (
                    market_date,
                    row_count,
                    expected_count,
                )
            )


    # ==================================================
    # PERIOD SEQUENCE VALIDATION
    # ==================================================

    invalid_period_ranges = []


    for (
        market_date,
        minimum_period,
        maximum_period,
        distinct_periods,
    ) in period_ranges:

        market_date = str(
            market_date
        )

        expected_count = (
            expected_periods_for_date(
                market_date
            )
        )


        if (
            minimum_period != 1
            or maximum_period
            != expected_count
            or distinct_periods
            != expected_count
        ):

            invalid_period_ranges.append(
                (
                    market_date,
                    minimum_period,
                    maximum_period,
                    distinct_periods,
                    expected_count,
                )
            )


    # ==================================================
    # REPORT
    # ==================================================

    print("=" * 55)

    print(
        "ELECTRICITY LOAD DATABASE VALIDATION"
    )

    print("=" * 55)


    print(
        f"PT total rows: "
        f"{total_rows}"
    )

    print(
        f"PT market days: "
        f"{total_days}"
    )

    print(
        f"First date: "
        f"{first_date}"
    )

    print(
        f"Last date: "
        f"{last_date}"
    )


    print()

    print(
        "Source / interval:"
    )


    for (
        source,
        interval,
        row_count,
    ) in source_counts:

        print(
            f"  {source} "
            f"| {interval} min "
            f"| {row_count} rows"
        )


    print()

    print(
        "Load range:"
    )

    print(
        f"  Minimum: "
        f"{minimum_load:.3f} MW"
    )

    print(
        f"  Maximum: "
        f"{maximum_load:.3f} MW"
    )


    print()

    print(
        "Missing calendar dates:"
    )


    if missing_dates:

        for date in missing_dates:

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
        "DST-aware row count:"
    )


    if unexpected_days:

        for (
            market_date,
            actual,
            expected,
        ) in unexpected_days:

            print(
                f"  {market_date}: "
                f"{actual} rows "
                f"(expected {expected})"
            )

    else:

        print(
            "  None"
        )


    print()

    print(
        "Days with invalid "
        "period sequence:"
    )


    if invalid_period_ranges:

        for (
            market_date,
            minimum,
            maximum,
            distinct,
            expected,
        ) in invalid_period_ranges:

            print(
                f"  {market_date}: "
                f"min={minimum}, "
                f"max={maximum}, "
                f"distinct={distinct}, "
                f"expected={expected}"
            )

    else:

        print(
            "  None"
        )


    print()

    print(
        f"Rows containing null values: "
        f"{null_rows}"
    )


    print(
        f"Duplicate timestamp/country rows: "
        f"{len(duplicate_rows)}"
    )


    # ==================================================
    # FINAL STATUS
    # ==================================================

    validation_passed = (
        len(missing_dates) == 0
        and len(unexpected_days) == 0
        and len(invalid_period_ranges) == 0
        and null_rows == 0
        and len(duplicate_rows) == 0
    )


    print()
    print("=" * 55)


    if validation_passed:

        print(
            "VALIDATION PASSED"
        )

    else:

        print(
            "VALIDATION FAILED"
        )


    print("=" * 55)


if __name__ == "__main__":

    validate_database()