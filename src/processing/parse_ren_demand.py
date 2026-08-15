import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd


RAW_DIR = (
    Path("data")
    / "raw"
    / "ren"
)

PROCESSED_DIR = (
    Path("data")
    / "processed"
    / "ren"
)


def process_ren_demand(
    date: str,
    force: bool = False,
) -> Path:

    raw_path = (
        RAW_DIR
        / f"market_load_{date}.xml"
    )

    if not raw_path.exists():

        raise FileNotFoundError(
            f"REN raw file not found: "
            f"{raw_path}"
        )


    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_path = (
        PROCESSED_DIR
        / f"actual_load_{date}.csv"
    )


    if (
        output_path.exists()
        and not force
    ):

        print(
            "Processed REN file already exists, "
            f"skipping processing: {output_path}"
        )

        return output_path


    # --------------------------------------------------
    # READ SOAP RESPONSE
    # --------------------------------------------------

    soap_root = ET.parse(
        raw_path
    ).getroot()


    result_element = None


    for element in soap_root.iter():

        if element.tag.endswith(
            "GetInfoForTimeFrameByInfoTypeResult"
        ):

            result_element = element
            break


    if result_element is None:

        raise ValueError(
            "Could not find REN result element."
        )


    if not result_element.text:

        raise ValueError(
            "REN result is empty."
        )


    # The actual REN XML is stored as text
    # inside the SOAP response.
    inner_xml = (
        result_element.text.strip()
    )


    inner_root = ET.fromstring(
        inner_xml
    )


    # --------------------------------------------------
    # CHECK REN APPLICATION ERROR
    # --------------------------------------------------

    error = inner_root.find(
        ".//Error"
    )


    if error is not None:

        code = error.findtext(
            "Code"
        )

        message = error.findtext(
            "Message"
        )

        raise RuntimeError(
            f"REN error {code}: {message}"
        )


    # --------------------------------------------------
    # EXTRACT OBSERVATIONS
    # --------------------------------------------------

    items = inner_root.findall(
        ".//Item"
    )


    if not items:

        raise ValueError(
            "No REN observations found."
        )


    rows = []


    for item in items:

        rows.append(
            {
                "market_date": item.findtext(
                    "MARKETDAY"
                ),

                "period": item.findtext(
                    "PERIOD"
                ),

                "timestamp_utc": item.findtext(
                    "UTCDATE"
                ),

                "load_mw": item.findtext(
                    "MARKETLOAD"
                ),
            }
        )


    df = pd.DataFrame(
        rows
    )


    # --------------------------------------------------
    # CONVERT DATA TYPES
    # --------------------------------------------------

    df["period"] = pd.to_numeric(
        df["period"]
    )


    df["load_mw"] = pd.to_numeric(
        df["load_mw"]
    )


    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
    )


    # REN market periods use CET/CEST.
    df["timestamp_market"] = (
        df["timestamp_utc"]
        .dt
        .tz_convert(
            "Europe/Madrid"
        )
    )


    # Standardize the date format with
    # the OMIE database: YYYYMMDD.
    df["market_date"] = (
        pd.to_datetime(
            df["market_date"]
        )
        .dt
        .strftime("%Y%m%d")
    )


    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    if df.isnull().any().any():

        raise ValueError(
            "Null values found in REN load data."
        )


    if df["period"].duplicated().any():

        raise ValueError(
            "Duplicate REN periods found."
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
            "REN periods are not sequential."
        )


    if len(df) not in {
        92,
        96,
        100,
    }:

        raise ValueError(
            "Unexpected number of REN periods: "
            f"{len(df)}"
        )


    if df["market_date"].nunique() != 1:

        raise ValueError(
            "More than one market date "
            "found in REN file."
        )


    if (
        df["market_date"].iloc[0]
        != date
    ):

        raise ValueError(
            "REN market date does not match "
            f"requested date {date}."
        )


    # --------------------------------------------------
    # ADD STANDARDIZED METADATA
    # --------------------------------------------------

    df["country"] = "PT"

    df["source"] = "REN"

    df["interval_minutes"] = 15


    # --------------------------------------------------
    # STANDARDIZED COLUMN ORDER
    # --------------------------------------------------

    processed_df = df[
        [
            "timestamp_utc",
            "timestamp_market",
            "market_date",
            "period",
            "country",
            "load_mw",
            "source",
            "interval_minutes",
        ]
    ]


    processed_df.to_csv(
        output_path,
        index=False,
    )


    print(
        "REN validation passed!"
    )


    print(
        f"Observations processed: "
        f"{len(processed_df)}"
    )


    print(
        f"Processed REN data saved to: "
        f"{output_path}"
    )


    print()
    print(
        "First 5 observations:"
    )

    print(
        processed_df.head()
        .to_string(index=False)
    )


    return output_path


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Process Portuguese "
            "15-minute actual electricity "
            "load from REN."
        )
    )


    parser.add_argument(
        "date",
        help=(
            "Market date in "
            "YYYYMMDD format."
        ),
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


    process_ren_demand(
        date=args.date,
        force=args.force,
    )


if __name__ == "__main__":
    main()