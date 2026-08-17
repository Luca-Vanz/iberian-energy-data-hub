import argparse
from datetime import datetime
from pathlib import Path
import json

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = (
    "https://servicebus.ren.pt/"
    "datahubapi/electricity/"
    "ElectricityProductionBreakdownDaily"
)


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


def create_session() -> requests.Session:

    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=[
            "GET",
        ],
        raise_on_status=False,
    )


    adapter = HTTPAdapter(
        max_retries=retry_strategy
    )


    session = requests.Session()


    session.mount(
        "https://",
        adapter,
    )

    session.mount(
        "http://",
        adapter,
    )


    return session


def download_ren_generation(
    date: str,
    force: bool = False,
) -> Path:

    market_date = datetime.strptime(
        date,
        "%Y%m%d",
    )


    date_iso = market_date.strftime(
        "%Y-%m-%d"
    )


    output_dir = (
        Path("data")
        / "raw"
        / "ren"
        / "generation"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_path = (
        output_dir
        / f"generation_{date}.json"
    )


    if (
        output_path.exists()
        and not force
    ):

        print(
            "Raw REN generation file "
            "already exists, skipping download: "
            f"{output_path}"
        )

        return output_path


    parameters = {
        "culture": "en-US",
        "date": date_iso,
    }


    print(
        f"Requesting REN generation mix "
        f"for {date}..."
    )


    session = create_session()


    response = session.get(
        BASE_URL,
        params=parameters,
        timeout=30,
    )


    print(
        f"REN response status: "
        f"{response.status_code}"
    )


    response.raise_for_status()


    try:
        data = response.json()

    except requests.exceptions.JSONDecodeError as exc:
        raise RuntimeError(
            "REN did not return valid JSON."
        ) from exc


    # --------------------------------------------------
    # BASIC RESPONSE VALIDATION
    # --------------------------------------------------

    if "xAxis" not in data:
        raise RuntimeError(
            "REN response does not contain xAxis."
        )


    if "series" not in data:
        raise RuntimeError(
            "REN response does not contain series."
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
        raise RuntimeError(
            f"REN returned no time periods "
            f"for {date}."
        )


    if not series:
        raise RuntimeError(
            f"REN returned no generation series "
            f"for {date}."
        )


    # --------------------------------------------------
    # SAVE RAW JSON
    # --------------------------------------------------

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


    print(
        f"Raw REN generation saved to: "
        f"{output_path}"
    )


    print(
        f"Time periods returned: "
        f"{len(categories)}"
    )


    print(
        f"Series returned: "
        f"{len(series)}"
    )


    print()
    print(
        "Series names:"
    )


    for item in series:

        print(
            f"  {item.get('name')}"
        )


    return output_path


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Download Portuguese "
            "electricity production breakdown "
            "from REN DataHub."
        )
    )


    parser.add_argument(
        "date",
        type=valid_date,
        help=(
            "Date in YYYYMMDD format."
        ),
    )


    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Download the raw file again "
            "even if it already exists."
        ),
    )


    args = parser.parse_args()


    download_ren_generation(
        date=args.date,
        force=args.force,
    )


if __name__ == "__main__":
    main()