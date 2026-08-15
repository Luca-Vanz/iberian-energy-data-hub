import sqlite3
from pathlib import Path


DATABASE_PATH = (
    Path("data")
    / "database"
    / "iberian_energy.db"
)


def validate_database():
    with sqlite3.connect(DATABASE_PATH) as connection:

        # --------------------------------------------------
        # TOTAL NUMBER OF ROWS
        # --------------------------------------------------

        total_rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM omie_day_ahead_prices;
            """
        ).fetchone()[0]


        # --------------------------------------------------
        # NUMBER OF MARKET DAYS
        # --------------------------------------------------

        total_days = connection.execute(
            """
            SELECT COUNT(DISTINCT market_date)
            FROM omie_day_ahead_prices;
            """
        ).fetchone()[0]


        # --------------------------------------------------
        # FIRST AND LAST DATE
        # --------------------------------------------------

        date_range = connection.execute(
            """
            SELECT
                MIN(market_date),
                MAX(market_date)
            FROM omie_day_ahead_prices;
            """
        ).fetchone()


        # --------------------------------------------------
        # CHECK ROW COUNT FOR EACH DAY
        # --------------------------------------------------

        incomplete_days = connection.execute(
            """
            SELECT
                market_date,
                COUNT(*) AS row_count

            FROM omie_day_ahead_prices

            GROUP BY market_date

            HAVING COUNT(*) != 192

            ORDER BY market_date;
            """
        ).fetchall()


        # --------------------------------------------------
        # CHECK ES/PT ROW COUNTS
        # --------------------------------------------------

        zone_counts = connection.execute(
            """
            SELECT
                bidding_zone,
                COUNT(*) AS row_count

            FROM omie_day_ahead_prices

            GROUP BY bidding_zone

            ORDER BY bidding_zone;
            """
        ).fetchall()


    print("=" * 50)
    print("OMIE DATABASE VALIDATION")
    print("=" * 50)

    print(f"Total rows: {total_rows}")
    print(f"Market days: {total_days}")
    print(f"First date: {date_range[0]}")
    print(f"Last date: {date_range[1]}")

    print()
    print("Rows by bidding zone:")

    for zone, row_count in zone_counts:
        print(
            f"  {zone}: {row_count}"
        )


    print()
    print("Days with unexpected row count:")

    if incomplete_days:

        for market_date, row_count in incomplete_days:
            print(
                f"  {market_date}: "
                f"{row_count} rows"
            )

    else:
        print(
            "  None - all days contain 192 rows."
        )


if __name__ == "__main__":
    validate_database()