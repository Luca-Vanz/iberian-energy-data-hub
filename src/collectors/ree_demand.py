import argparse
import json
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = (
    "https://apidatos.ree.es/es/datos/"
    "demanda/demanda-tiempo-real"
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


def download_ree_demand(
    date: str,
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
        / "ree"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_path = (
        output_dir
        / f"demand_{date}.json"
    )


    params = {
        "start_date": (
            f"{date_iso}T00:00"
        ),
        "end_date": (
            f"{date_iso}T23:59"
        ),
        "time_trunc": "hour",
        "geo_trunc": "electric_system",
        "geo_limit": "peninsular",
        "geo_ids": "8741",
    }


    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


    print(
        f"Requesting REE demand data "
        f"for {date}..."
    )


    session = create_session()


    response = session.get(
        BASE_URL,
        params=params,
        headers=headers,
        timeout=30,
    )


    print(
        f"REE response status: "
        f"{response.status_code}"
    )


    if not response.ok:

        print()
        print(
            "REE request failed."
        )

        print(
            f"Request URL: "
            f"{response.url}"
        )

        print()

        print(
            "Response body:"
        )

        print(
            response.text[:1000]
        )

        response.raise_for_status()


    data = response.json()


    output_path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


    print(
        f"Raw REE demand data saved to: "
        f"{output_path}"
    )


    print()
    print(
        "Series returned by REE:"
    )


    for series in data.get(
        "included",
        [],
    ):

        attributes = series.get(
            "attributes",
            {},
        )

        title = attributes.get(
            "title"
        )

        magnitude = attributes.get(
            "magnitude"
        )

        values = attributes.get(
            "values",
            [],
        )


        print(
            f"  {title} "
            f"| magnitude: {magnitude} "
            f"| observations: {len(values)}"
        )


    return output_path


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Download hourly Spanish "
            "electricity demand from REE."
        )
    )


    parser.add_argument(
        "date",
        type=valid_date,
        help=(
            "Date in YYYYMMDD format."
        ),
    )


    args = parser.parse_args()


    download_ree_demand(
        date=args.date,
    )


if __name__ == "__main__":
    main()