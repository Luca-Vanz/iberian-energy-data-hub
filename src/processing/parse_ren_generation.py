import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


# ==================================================
# CONFIGURATION
# ==================================================

GENERATION_TECHNOLOGIES = {
    "Hydro": "hydro",
    "Solar": "solar",
    "Wind": "wind",
    "Natural Gas": "natural_gas",
    "Other Thermal": "other_thermal",
    "Biomass": "biomass",
    "Coal": "coal",
    "Wave": "wave",
}


# ==================================================
# DATE VALIDATION
# ==================================================

def valid_date(value: str) -> str:

    try:
        datetime.strptime(
            value,
            "%Y%m%d",
        )

    except ValueError as exc:

        raise argparse.ArgumentTypeError(
            "Date must be a valid calendar "
            "date in YYYYMMDD format."
        ) from exc

    return value


# ==================================================
# PROCESS REN GENERATION
# ==================================================

def process_ren_generation(
    date: str,
    force: bool = False,
) -> Path:

    raw_path = (
        Path("data")
        / "raw"
        / "ren"
        / "generation"
        / f"generation_{date}.json"
    )


    output_dir = (
        Path("data")
        / "processed"
        / "ren"
        / "generation"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_path = (
        output_dir
        / f"generation_{date}.csv"
    )


    # --------------------------------------------------
    # CHECK INPUT / EXISTING OUTPUT
    # --------------------------------------------------

    if not raw_path.exists():

        raise FileNotFoundError(
            f"Raw REN generation file not found: "
            f"{raw_path}"
        )


    if (
        output_path.exists()
        and not force
    ):

        print(
            "Processed REN generation file "
            "already exists, skipping processing: "
            f"{output_path}"
        )

        return output_path


    # --------------------------------------------------
    # READ RAW JSON
    # --------------------------------------------------

    with raw_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(
            file
        )


    categories = (
        data
        .get("xAxis", {})
        .get("categories", [])
    )


    series = data.get(
        "series",
        []
    )


    if not categories:

        raise ValueError(
            "REN generation data contains "
            "no time categories."
        )


    if not series:

        raise ValueError(
            "REN generation data contains "
            "no series."
        )


    # --------------------------------------------------
    # EXPECTED 15-MINUTE TIMESTAMPS
    # --------------------------------------------------

    market_date = pd.to_datetime(
        date,
        format="%Y%m%d",
    )


    next_date = (
        market_date
        + pd.Timedelta(days=1)
    )


    timestamps_market = pd.date_range(
        start=market_date,
        end=next_date,
        freq="15min",
        inclusive="left",
        tz="Europe/Madrid",
    )


    expected_periods = len(
        timestamps_market
    )


    actual_periods = len(
        categories
    )


    if (
        actual_periods
        != expected_periods
    ):

        raise ValueError(
            f"Unexpected REN period count "
            f"for {date}: "
            f"{actual_periods} returned, "
            f"{expected_periods} expected."
        )


    # --------------------------------------------------
    # BUILD SERIES LOOKUP
    # --------------------------------------------------

    series_lookup = {
        item.get("name"): item
        for item in series
    }


    missing_series = [
        source_name
        for source_name
        in GENERATION_TECHNOLOGIES
        if source_name
        not in series_lookup
    ]


    if missing_series:

        raise ValueError(
            "Expected REN generation series "
            "not found: "
            + ", ".join(
                missing_series
            )
        )


    # --------------------------------------------------
    # NORMALIZE GENERATION DATA
    # --------------------------------------------------

    rows = []


    for (
        source_name,
        technology,
    ) in GENERATION_TECHNOLOGIES.items():

        series_item = (
            series_lookup[
                source_name
            ]
        )


        values = series_item.get(
            "data",
            []
        )


        if (
            len(values)
            != expected_periods
        ):

            raise ValueError(
                f"Series '{source_name}' has "
                f"{len(values)} values; "
                f"expected {expected_periods}."
            )


        for index, value in enumerate(
            values
        ):

            rows.append(
                {
                    "timestamp_utc":
                        timestamps_market[
                            index
                        ].tz_convert(
                            "UTC"
                        ),

                    "timestamp_market":
                        timestamps_market[
                            index
                        ],

                    "market_date":
                        date,

                    "period":
                        index + 1,

                    "country":
                        "PT",

                    "technology":
                        technology,

                    "generation_mw":
                        value,

                    "source":
                        "REN",

                    "interval_minutes":
                        15,
                }
            )


    df = pd.DataFrame(
        rows
    )


    # ==================================================
    # VALIDATION
    # ==================================================

    expected_rows = (
        expected_periods
        * len(
            GENERATION_TECHNOLOGIES
        )
    )


    if len(df) != expected_rows:

        raise ValueError(
            f"Unexpected number of normalized rows: "
            f"{len(df)}; "
            f"expected {expected_rows}."
        )


    if df.isnull().any().any():

        null_counts = (
            df.isnull()
            .sum()
        )


        null_counts = (
            null_counts[
                null_counts > 0
            ]
        )


        raise ValueError(
            "Null values found in REN generation data:\n"
            f"{null_counts}"
        )


    if (
        df["generation_mw"]
        .apply(
            lambda value:
                isinstance(
                    value,
                    (int, float)
                )
        )
        .all()
        is False
    ):

        raise ValueError(
            "Non-numeric generation values found."
        )


    duplicate_count = (
        df.duplicated(
            subset=[
                "timestamp_utc",
                "country",
                "technology",
            ]
        )
        .sum()
    )


    if duplicate_count > 0:

        raise ValueError(
            f"Found {duplicate_count} duplicate "
            "timestamp/country/technology rows."
        )


    technology_counts = (
        df.groupby(
            "technology"
        )
        .size()
    )


    invalid_technologies = (
        technology_counts[
            technology_counts
            != expected_periods
        ]
    )


    if not invalid_technologies.empty:

        raise ValueError(
            "Unexpected number of periods "
            "for one or more technologies:\n"
            f"{invalid_technologies}"
        )


    # --------------------------------------------------
    # SAVE PROCESSED DATA
    # --------------------------------------------------

    df.to_csv(
        output_path,
        index=False,
    )


    print(
        "REN generation validation passed!"
    )


    print(
        f"Market periods: "
        f"{expected_periods}"
    )


    print(
        f"Generation technologies: "
        f"{len(GENERATION_TECHNOLOGIES)}"
    )


    print(
        f"Normalized rows: "
        f"{len(df)}"
    )


    print(
        f"Processed REN generation saved to: "
        f"{output_path}"
    )


    print()

    print(
        "Rows by technology:"
    )


    for (
        technology,
        count,
    ) in technology_counts.items():

        print(
            f"  {technology}: "
            f"{count}"
        )


    print()

    print(
        "First 16 observations:"
    )


    print(
        df.head(16)
        .to_string(
            index=False
        )
    )


    return output_path


# ==================================================
# COMMAND LINE
# ==================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Process Portuguese "
            "15-minute electricity generation "
            "by technology from REN."
        )
    )


    parser.add_argument(
        "date",
        type=valid_date,
        help=(
            "Market date in "
            "YYYYMMDD format."
        ),
    )


    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Process the raw file again "
            "even if processed output exists."
        ),
    )


    args = parser.parse_args()


    process_ren_generation(
        date=args.date,
        force=args.force,
    )


if __name__ == "__main__":

    main()