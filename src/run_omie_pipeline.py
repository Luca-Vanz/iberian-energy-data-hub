import argparse
from datetime import datetime

from src.collectors.omie_day_ahead import download_omie_day_ahead
from src.processing.parse_omie_day_ahead import process_omie_day_ahead

def valid_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Date must be a valid calendar date in YYYYMMDD format."
        ) from exc

    return value

def run_pipeline(date: str):
    print(f"Running OMIE day-ahead pipeline for {date}")
    print()

    download_omie_day_ahead(date)

    print()

    process_omie_day_ahead(date)

    print()
    print("Pipeline completed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="Download and process OMIE day-ahead electricity prices."
    )

    parser.add_argument(
    "date",
    type=valid_date,
    help="Market date in YYYYMMDD format, for example 20260813",
)

    args = parser.parse_args()

    run_pipeline(args.date)


if __name__ == "__main__":
    main()