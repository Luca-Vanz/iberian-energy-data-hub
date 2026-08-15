import argparse
from datetime import datetime, timedelta
from pathlib import Path

from src.collectors.omie_day_ahead import download_omie_day_ahead
from src.database.load_omie_prices import create_database, load_omie_prices
from src.processing.parse_omie_day_ahead import process_omie_day_ahead


LOG_DIR = Path("data") / "logs"


def valid_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Date must be a valid calendar date in YYYYMMDD format."
        ) from exc

    return value


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

    if final_date < current_date:
        raise ValueError(
            "End date cannot be before start date."
        )

    dates = []

    while current_date <= final_date:
        dates.append(
            current_date.strftime("%Y%m%d")
        )

        current_date += timedelta(days=1)

    return dates


def save_failure_log(
    start_date: str,
    end_date: str,
    failures: list[dict],
) -> Path:

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    log_path = (
        LOG_DIR
        / f"omie_failures_{start_date}_{end_date}_{timestamp}.txt"
    )

    with log_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            "OMIE pipeline failure report\n"
        )

        file.write(
            f"Range: {start_date} to {end_date}\n"
        )

        file.write(
            f"Failed dates: {len(failures)}\n"
        )

        file.write("\n")

        for failure in failures:

            file.write(
                f"Date: {failure['date']}\n"
            )

            file.write(
                f"Error type: {failure['error_type']}\n"
            )

            file.write(
                f"Error: {failure['error_message']}\n"
            )

            file.write(
                "-" * 50
                + "\n"
            )

    return log_path


def run_pipeline(
    start_date: str,
    end_date: str | None = None,
    force: bool = False,
):
    if end_date is None:
        end_date = start_date

    dates = generate_dates(
        start_date,
        end_date,
    )

    successful_dates = []
    failures = []

    print(
        f"Running OMIE pipeline from "
        f"{start_date} to {end_date} "
        f"({len(dates)} day(s))"
    )

    print()

    create_database()

    print()

    for index, date in enumerate(
        dates,
        start=1,
    ):

        print(
            f"[{index}/{len(dates)}] "
            f"Processing {date}"
        )

        try:

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
            load_omie_prices(
                date
            )

            successful_dates.append(
                date
            )

            print(
                f"Completed {date}"
            )

        except Exception as exc:

            failure = {
                "date": date,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }

            failures.append(
                failure
            )

            print(
                f"ERROR processing {date}"
            )

            print(
                f"{type(exc).__name__}: {exc}"
            )

            print(
                "Continuing with next date..."
            )

        print(
            "-" * 50
        )


    print()
    print("=" * 50)
    print("PIPELINE SUMMARY")
    print("=" * 50)

    print(
        f"Requested dates: "
        f"{len(dates)}"
    )

    print(
        f"Successful dates: "
        f"{len(successful_dates)}"
    )

    print(
        f"Failed dates: "
        f"{len(failures)}"
    )


    if failures:

        print()
        print(
            "Failed dates:"
        )

        for failure in failures:

            print(
                f"  {failure['date']} "
                f"- {failure['error_type']}: "
                f"{failure['error_message']}"
            )


        log_path = save_failure_log(
            start_date=start_date,
            end_date=end_date,
            failures=failures,
        )

        print()
        print(
            f"Failure log saved to: "
            f"{log_path}"
        )

    else:

        print()
        print(
            "All dates completed successfully."
        )


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
        help=(
            "First market date "
            "in YYYYMMDD format."
        ),
    )


    parser.add_argument(
        "end_date",
        nargs="?",
        type=valid_date,
        help=(
            "Optional final market date "
            "in YYYYMMDD format."
        ),
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
        start_date=args.start_date,
        end_date=args.end_date,
        force=args.force,
    )


if __name__ == "__main__":
    main()