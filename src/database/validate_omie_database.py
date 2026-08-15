import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)

VALID_ROWS_PER_DAY = {
    184,
    192,
    200,
}

VALID_ROWS_PER_ZONE = {
    92,
    96,
    100,
}


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
            current_date.strftime("%Y%m%d")
        )

        current_date += timedelta(days=1)

    return dates


def validate_database():

    with sqlite3.connect(DATABASE_PATH) as connection:

        # --------------------------------------------------
        # BASIC DATABASE INFORMATION
        # --------------------------------------------------

        total_rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM omie_day_ahead_prices;
            """
        ).fetchone()[0]


        total_days = connection.execute(
            """
            SELECT COUNT(DISTINCT market_date)
            FROM omie_day_ahead_prices;
            """
        ).fetchone()[0]


        first_date, last_date = connection.execute(
            """
            SELECT
                MIN(market_date),
                MAX(market_date)

            FROM omie_day_ahead_prices;
            """
        ).fetchone()


        # --------------------------------------------------
        # ALL DATES PRESENT IN DATABASE
        # --------------------------------------------------

        database_dates = connection.execute(
            """
            SELECT DISTINCT market_date

            FROM omie_day_ahead_prices

            ORDER BY market_date;
            """
        ).fetchall()

        database_dates = {
            row[0]
            for row in database_dates
        }


        # --------------------------------------------------
        # CHECK TOTAL ROW COUNT FOR EACH DAY
        # --------------------------------------------------

        daily_counts = connection.execute(
            """
            SELECT
                market_date,
                COUNT(*) AS row_count

            FROM omie_day_ahead_prices

            GROUP BY market_date

            ORDER BY market_date;
            """
        ).fetchall()


        unexpected_days = [
            (market_date, row_count)
            for market_date, row_count
            in daily_counts
            if row_count not in VALID_ROWS_PER_DAY
        ]


        # --------------------------------------------------
        # CHECK EACH BIDDING ZONE
        # --------------------------------------------------

        zone_daily_counts = connection.execute(
            """
            SELECT
                market_date,
                bidding_zone,
                COUNT(*) AS row_count

            FROM omie_day_ahead_prices

            GROUP BY
                market_date,
                bidding_zone

            ORDER BY
                market_date,
                bidding_zone;
            """
        ).fetchall()


        unexpected_zone_counts = [
            (
                market_date,
                bidding_zone,
                row_count,
            )
            for (
                market_date,
                bidding_zone,
                row_count,
            )
            in zone_daily_counts
            if row_count not in VALID_ROWS_PER_ZONE
        ]


        # --------------------------------------------------
        # TOTAL ROWS BY BIDDING ZONE
        # --------------------------------------------------

        zone_counts = connection.execute(
            """
            SELECT
                bidding_zone,
                COUNT(*)

            FROM omie_day_ahead_prices

            GROUP BY bidding_zone

            ORDER BY bidding_zone;
            """
        ).fetchall()


    # --------------------------------------------------
    # CHECK MISSING CALENDAR DATES
    # --------------------------------------------------

    expected_dates = set(
        generate_expected_dates(
            first_date,
            last_date,
        )
    )

    missing_dates = sorted(
        expected_dates - database_dates
    )


    # --------------------------------------------------
    # PRINT REPORT
    # --------------------------------------------------

    print("=" * 50)
    print("OMIE DATABASE VALIDATION")
    print("=" * 50)

    print(
        f"Total rows: {total_rows}"
    )

    print(
        f"Market days: {total_days}"
    )

    print(
        f"First date: {first_date}"
    )

    print(
        f"Last date: {last_date}"
    )


    print()
    print("Rows by bidding zone:")

    for zone, row_count in zone_counts:

        print(
            f"  {zone}: {row_count}"
        )


    print()
    print("Missing calendar dates:")

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
    print("Days with unexpected total row count:")

    if unexpected_days:

        for market_date, row_count in unexpected_days:

            print(
                f"  {market_date}: "
                f"{row_count} rows"
            )

    else:

        print(
            "  None"
        )


    print()
    print("Zone/day combinations with unexpected row count:")

    if unexpected_zone_counts:

        for (
            market_date,
            bidding_zone,
            row_count,
        ) in unexpected_zone_counts:

            print(
                f"  {market_date} "
                f"{bidding_zone}: "
                f"{row_count} rows"
            )

    else:

        print(
            "  None"
        )


if __name__ == "__main__":
    validate_database()