import argparse
from pathlib import Path

import pandas as pd


FILE_PREFIX = "marginalpdbc"


def find_raw_file(
    date: str,
) -> Path:

    raw_dir = (
        Path("data")
        / "raw"
        / "omie"
    )


    matching_files = list(
        raw_dir.glob(
            f"{FILE_PREFIX}_{date}.*"
        )
    )


    valid_files = []


    for path in matching_files:

        try:
            revision = int(
                path.suffix[1:]
            )

        except ValueError:
            continue


        valid_files.append(
            (revision, path)
        )


    if not valid_files:

        raise FileNotFoundError(
            f"No raw OMIE file found "
            f"for {date}."
        )


    valid_files.sort(
        key=lambda item: item[0],
        reverse=True,
    )


    return valid_files[0][1]


def process_omie_day_ahead(
    date: str,
    force: bool = False,
) -> Path:

    raw_path = find_raw_file(
        date
    )


    processed_dir = (
        Path("data")
        / "processed"
        / "omie"
    )


    processed_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_path = (
        processed_dir
        / f"day_ahead_prices_{date}.csv"
    )


    if (
        output_path.exists()
        and not force
    ):

        print(
            "Processed file already exists, "
            f"skipping processing: {output_path}"
        )

        return output_path


    print(
        f"Using raw OMIE file: {raw_path}"
    )


    df = pd.read_csv(
        raw_path,
        sep=";",
        skiprows=1,
        skipfooter=1,
        header=None,
        usecols=range(6),
        names=[
            "year",
            "month",
            "day",
            "period",
            "price_pt_eur_mwh",
            "price_es_eur_mwh",
        ],
        engine="python",
    )


    df["date"] = pd.to_datetime(
        df[
            [
                "year",
                "month",
                "day",
            ]
        ]
    )


    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    if df.isnull().any().any():

        raise ValueError(
            "Null values found in OMIE data."
        )


    if df["period"].duplicated().any():

        raise ValueError(
            "Duplicate OMIE periods found."
        )


    expected_periods = list(
        range(
            1,
            len(df) + 1,
        )
    )


    if (
        df["period"].tolist()
        != expected_periods
    ):

        raise ValueError(
            "OMIE periods are not sequential."
        )


    if len(df) not in {
        92,
        96,
        100,
    }:

        raise ValueError(
            "Unexpected number of OMIE periods: "
            f"{len(df)}"
        )


    # --------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------

    market_date = df[
        "date"
    ].iloc[0]


    next_date = (
        market_date
        + pd.Timedelta(days=1)
    )


    timestamps = pd.date_range(
        start=market_date,
        end=next_date,
        freq="15min",
        inclusive="left",
        tz="Europe/Madrid",
    )


    if len(timestamps) != len(df):

        raise ValueError(
            "Timestamp count does not match "
            "OMIE period count."
        )


    df["timestamp_market"] = (
        timestamps
    )


    df["timestamp_utc"] = (
        df["timestamp_market"]
        .dt
        .tz_convert("UTC")
    )


    # --------------------------------------------------
    # STANDARDIZED OUTPUT
    # --------------------------------------------------

    processed_df = df[
        [
            "timestamp_utc",
            "timestamp_market",
            "period",
            "price_es_eur_mwh",
            "price_pt_eur_mwh",
        ]
    ]


    processed_df.to_csv(
        output_path,
        index=False,
    )


    print(
        "Validation passed!"
    )


    print(
        f"Processed data saved to: "
        f"{output_path}"
    )


    return output_path


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Process OMIE day-ahead "
            "electricity prices."
        )
    )


    parser.add_argument(
        "date",
        help="Market date in YYYYMMDD format.",
    )


    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Process the file again "
            "even if output already exists."
        ),
    )


    args = parser.parse_args()


    process_omie_day_ahead(
        date=args.date,
        force=args.force,
    )


if __name__ == "__main__":
    main()