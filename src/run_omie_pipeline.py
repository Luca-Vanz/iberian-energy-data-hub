import argparse
from datetime import datetime, timedelta

from src.collectors.omie_day_ahead import download_omie_day_ahead
from src.database.load_omie_prices import create_database, load_omie_prices
from src.processing.parse_omie_day_ahead import process_omie_day_ahead


def valid_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Date must be a valid calendar date in YYYYMMDD format."
        ) from exc

    return value


def generate_dates(start_date: str, end_date: str):
    current_date = datetime.strptime(start_date, "%Y%m%d")
    final_date = datetime.strptime(end_date, "%Y%m%d")

    if final_date < current_date:
        raise ValueError(
            "End date cannot be before start date."
        )

    dates = []

    while current_date <= final_date:
        dates.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)

    return dates


def run_pipeline(
    start_date: str,
    end_date: str | None = None,
    force: bool = False,
):
    if end_date is None:
        end_date = start_date

    dates = generate_dates(start_date, end_date)

    print(
        f"Running OMIE pipeline from {start_date} "
        f"to {end_date} ({len(dates)} day(s))"
    )
    print()

    # Create the SQLite database/table if needed
    create_database()
    print()

    for date in dates:
        print(f"Processing {date}")

        # 1. Extract
        download_omie_day_ahead(
            date,
            force=force,
        )

        # 2. Transform
        process_omie_day_ahead(
            date,
            force=force,
        )

        # 3. Load
        load_omie_prices(date)

        print(f"Completed {date}")
        print("-" * 50)

    print()
    print("Pipeline completed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Download, process and load OMIE "
            "day-ahead electricity prices."
        )
    )

    parser.add_argument(
        "start_date",
        type=valid_date,
        help="First market date in YYYYMMDD format.",
    )

    parser.add_argument(
        "end_date",
        nargs="?",
        type=valid_date,
        help="Optional final market date in YYYYMMDD format.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Download and process files again "
            "even if they already exist."
        ),
    )

    args = parser.parse_args()

    run_pipeline(
        args.start_date,
        args.end_date,
        force=args.force,
    )


if __name__ == "__main__":
    main()