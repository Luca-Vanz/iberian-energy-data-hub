import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


EXPECTED_TECHNOLOGIES = {
    "hydro",
    "solar",
    "wind",
    "natural_gas",
    "other_thermal",
    "biomass",
    "coal",
    "wave",
}


# ==================================================
# EXPECTED CALENDAR DATES
# ==================================================

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


# ==================================================
# EXPECTED PERIODS FOR SPECIFIC DATE
# ==================================================

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


# ==================================================
# DATABASE VALIDATION
# ==================================================

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
        # BASIC INFORMATION
        # ------------------------------------------

        total_rows = connection.execute(
            """
            SELECT COUNT(*)

            FROM electricity_generation

            WHERE country = 'PT';
            """
        ).fetchone()[0]


        total_days = connection.execute(
            """
            SELECT COUNT(
                DISTINCT market_date
            )

            FROM electricity_generation

            WHERE country = 'PT';
            """
        ).fetchone()[0]


        first_date, last_date = (
            connection.execute(
                """
                SELECT
                    MIN(market_date),
                    MAX(market_date)

                FROM electricity_generation

                WHERE country = 'PT';
                """
            ).fetchone()
        )


        if (
            first_date is None
            or last_date is None
        ):

            raise ValueError(
                "No Portuguese generation "
                "data found."
            )


        # ------------------------------------------
        # DATES PRESENT
        # ------------------------------------------

        database_dates = (
            connection.execute(
                """
                SELECT DISTINCT
                    market_date

                FROM electricity_generation

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
        # TECHNOLOGIES PRESENT
        # ------------------------------------------

        technology_counts = (
            connection.execute(
                """
                SELECT
                    technology,
                    COUNT(*)

                FROM electricity_generation

                WHERE country = 'PT'

                GROUP BY technology

                ORDER BY technology;
                """
            ).fetchall()
        )


        database_technologies = {
            row[0]
            for row in technology_counts
        }


        # ------------------------------------------
        # DAILY TOTAL ROW COUNTS
        # ------------------------------------------

        daily_counts = (
            connection.execute(
                """
                SELECT
                    market_date,
                    COUNT(*)

                FROM electricity_generation

                WHERE country = 'PT'

                GROUP BY market_date

                ORDER BY market_date;
                """
            ).fetchall()
        )


        # ------------------------------------------
        # DAILY COUNTS BY TECHNOLOGY
        # ------------------------------------------

        daily_technology_counts = (
            connection.execute(
                """
                SELECT
                    market_date,
                    technology,
                    COUNT(*)

                FROM electricity_generation

                WHERE country = 'PT'

                GROUP BY
                    market_date,
                    technology

                ORDER BY
                    market_date,
                    technology;
                """
            ).fetchall()
        )


        # ------------------------------------------
        # PERIOD RANGES
        # ------------------------------------------

        period_ranges = (
            connection.execute(
                """
                SELECT
                    market_date,
                    technology,
                    MIN(period),
                    MAX(period),
                    COUNT(
                        DISTINCT period
                    )

                FROM electricity_generation

                WHERE country = 'PT'

                GROUP BY
                    market_date,
                    technology

                ORDER BY
                    market_date,
                    technology;
                """
            ).fetchall()
        )


        # ------------------------------------------
        # NULL VALUES
        # ------------------------------------------

        null_rows = connection.execute(
            """
            SELECT COUNT(*)

            FROM electricity_generation

            WHERE
                country = 'PT'

                AND (
                    timestamp_utc IS NULL
                    OR timestamp_market IS NULL
                    OR market_date IS NULL
                    OR period IS NULL
                    OR technology IS NULL
                    OR generation_mw IS NULL
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
                    technology,
                    COUNT(*)

                FROM electricity_generation

                WHERE country = 'PT'

                GROUP BY
                    timestamp_utc,
                    country,
                    technology

                HAVING COUNT(*) > 1;
                """
            ).fetchall()
        )


        # ------------------------------------------
        # SOURCE / INTERVAL
        # ------------------------------------------

        source_counts = (
            connection.execute(
                """
                SELECT
                    source,
                    interval_minutes,
                    COUNT(*)

                FROM electricity_generation

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
        # GENERATION RANGES BY TECHNOLOGY
        # ------------------------------------------

        generation_ranges = (
            connection.execute(
                """
                SELECT
                    technology,

                    ROUND(
                        MIN(generation_mw),
                        3
                    ),

                    ROUND(
                        MAX(generation_mw),
                        3
                    )

                FROM electricity_generation

                WHERE country = 'PT'

                GROUP BY technology

                ORDER BY technology;
                """
            ).fetchall()
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
    # TECHNOLOGY COMPLETENESS
    # ==================================================

    missing_technologies = (
        EXPECTED_TECHNOLOGIES
        - database_technologies
    )


    unexpected_technologies = (
        database_technologies
        - EXPECTED_TECHNOLOGIES
    )


    # ==================================================
    # EXPECTED TOTAL ROW COUNT
    # ==================================================

    expected_total_periods = sum(
        expected_periods_for_date(
            date
        )
        for date
        in expected_dates
    )


    expected_total_rows = (
        expected_total_periods
        * len(EXPECTED_TECHNOLOGIES)
    )


    # ==================================================
    # DAILY TOTAL ROW VALIDATION
    # ==================================================

    unexpected_daily_counts = []


    for (
        market_date,
        actual_rows,
    ) in daily_counts:

        market_date = str(
            market_date
        )


        expected_periods = (
            expected_periods_for_date(
                market_date
            )
        )


        expected_rows = (
            expected_periods
            * len(EXPECTED_TECHNOLOGIES)
        )


        if actual_rows != expected_rows:

            unexpected_daily_counts.append(
                (
                    market_date,
                    actual_rows,
                    expected_rows,
                )
            )


    # ==================================================
    # DAILY TECHNOLOGY VALIDATION
    # ==================================================

    invalid_daily_technology_counts = []


    for (
        market_date,
        technology,
        actual_count,
    ) in daily_technology_counts:

        market_date = str(
            market_date
        )


        expected_count = (
            expected_periods_for_date(
                market_date
            )
        )


        if actual_count != expected_count:

            invalid_daily_technology_counts.append(
                (
                    market_date,
                    technology,
                    actual_count,
                    expected_count,
                )
            )


    # ==================================================
    # PERIOD SEQUENCE VALIDATION
    # ==================================================

    invalid_period_ranges = []


    for (
        market_date,
        technology,
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
            or maximum_period != expected_count
            or distinct_periods != expected_count
        ):

            invalid_period_ranges.append(
                (
                    market_date,
                    technology,
                    minimum_period,
                    maximum_period,
                    distinct_periods,
                    expected_count,
                )
            )


    # ==================================================
    # REPORT
    # ==================================================

    print("=" * 65)

    print(
        "ELECTRICITY GENERATION DATABASE VALIDATION"
    )

    print("=" * 65)


    print(
        f"PT total rows: "
        f"{total_rows}"
    )

    print(
        f"Expected total rows: "
        f"{expected_total_rows}"
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
        count,
    ) in source_counts:

        print(
            f"  {source} "
            f"| {interval} min "
            f"| {count} rows"
        )


    print()
    print(
        "Rows by technology:"
    )


    for (
        technology,
        count,
    ) in technology_counts:

        print(
            f"  {technology}: "
            f"{count}"
        )


    print()
    print(
        "Generation range by technology:"
    )


    for (
        technology,
        minimum,
        maximum,
    ) in generation_ranges:

        print(
            f"  {technology}: "
            f"{minimum} to "
            f"{maximum} MW"
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
        "Missing technologies:"
    )


    if missing_technologies:

        for technology in sorted(
            missing_technologies
        ):

            print(
                f"  {technology}"
            )

    else:

        print(
            "  None"
        )


    print()
    print(
        "Unexpected technologies:"
    )


    if unexpected_technologies:

        for technology in sorted(
            unexpected_technologies
        ):

            print(
                f"  {technology}"
            )

    else:

        print(
            "  None"
        )


    print()
    print(
        "Days with unexpected "
        "total row count:"
    )


    if unexpected_daily_counts:

        for (
            date,
            actual,
            expected,
        ) in unexpected_daily_counts:

            print(
                f"  {date}: "
                f"{actual} rows "
                f"(expected {expected})"
            )

    else:

        print(
            "  None"
        )


    print()
    print(
        "Date/technology combinations "
        "with unexpected row count:"
    )


    if invalid_daily_technology_counts:

        for (
            date,
            technology,
            actual,
            expected,
        ) in invalid_daily_technology_counts:

            print(
                f"  {date} | "
                f"{technology}: "
                f"{actual} "
                f"(expected {expected})"
            )

    else:

        print(
            "  None"
        )


    print()
    print(
        "Date/technology combinations "
        "with invalid period sequence:"
    )


    if invalid_period_ranges:

        for issue in (
            invalid_period_ranges
        ):

            print(
                f"  {issue}"
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
        f"Duplicate timestamp/country/"
        f"technology rows: "
        f"{len(duplicate_rows)}"
    )


    # ==================================================
    # FINAL STATUS
    # ==================================================

    validation_passed = (
        total_rows
        == expected_total_rows
        and total_days
        == len(expected_dates)
        and len(missing_dates) == 0
        and len(missing_technologies) == 0
        and len(unexpected_technologies) == 0
        and len(unexpected_daily_counts) == 0
        and len(
            invalid_daily_technology_counts
        ) == 0
        and len(invalid_period_ranges) == 0
        and null_rows == 0
        and len(duplicate_rows) == 0
    )


    print()
    print("=" * 65)


    if validation_passed:

        print(
            "VALIDATION PASSED"
        )

    else:

        print(
            "VALIDATION FAILED"
        )


    print("=" * 65)


if __name__ == "__main__":

    validate_database()