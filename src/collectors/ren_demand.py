import argparse
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = (
    "https://ws-mercado.ren.pt/"
    "MarketInfoService.asmx"
)

INFO_TYPE = "GetMarketLoadActual"


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
            "POST",
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


def download_ren_demand(
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
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_path = (
        output_dir
        / f"market_load_{date}.xml"
    )


    # Skip download if the raw file already exists.
    if (
        output_path.exists()
        and not force
    ):

        print(
            "Raw REN file already exists, "
            f"skipping download: {output_path}"
        )

        return output_path


    soap_body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope '
        'xmlns:soap="http://www.w3.org/2003/05/soap-envelope" '
        'xmlns:ws="https://ws-mercado.ren.pt">'
        '<soap:Header/>'
        '<soap:Body>'
        '<ws:GetInfoForTimeFrameByInfoType>'
        f'<ws:StartDay>{date_iso}</ws:StartDay>'
        f'<ws:EndDay>{date_iso}</ws:EndDay>'
        f'<ws:InfoType>{INFO_TYPE}</ws:InfoType>'
        '</ws:GetInfoForTimeFrameByInfoType>'
        '</soap:Body>'
        '</soap:Envelope>'
    )


    headers = {
        "Content-Type": (
            "application/soap+xml;"
            "charset=utf-8;"
            'action="https://ws-mercado.ren.pt/'
            'GetInfoForTimeFrameByInfoType"'
        )
    }


    print(
        f"Requesting REN market load "
        f"for {date}..."
    )


    session = create_session()


    response = session.post(
        BASE_URL,
        data=soap_body.encode("utf-8"),
        headers=headers,
        timeout=30,
    )


    print(
        f"REN response status: "
        f"{response.status_code}"
    )


    response.raise_for_status()


    # --------------------------------------------------
    # CHECK SOAP RESPONSE BEFORE SAVING
    # --------------------------------------------------

    soap_root = ET.fromstring(
        response.content
    )


    result_element = None


    for element in soap_root.iter():

        if element.tag.endswith(
            "GetInfoForTimeFrameByInfoTypeResult"
        ):

            result_element = element
            break


    if result_element is None:

        raise RuntimeError(
            "Could not find REN result "
            "inside SOAP response."
        )


    if not result_element.text:

        raise RuntimeError(
            "REN returned an empty result."
        )


    inner_xml = (
        result_element.text.strip()
    )


    inner_root = ET.fromstring(
        inner_xml
    )


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


    items = inner_root.findall(
        ".//Item"
    )


    if not items:

        raise RuntimeError(
            f"REN returned no observations "
            f"for {date}."
        )


    # Only save a response after we know
    # REN returned valid data.
    output_path.write_bytes(
        response.content
    )


    print(
        f"Raw REN response saved to: "
        f"{output_path}"
    )


    print(
        f"Observations returned: "
        f"{len(items)}"
    )


    return output_path


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Download Portuguese "
            "15-minute actual market load "
            "from REN."
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
            "Download the raw REN file again "
            "even if it already exists."
        ),
    )


    args = parser.parse_args()


    download_ren_demand(
        date=args.date,
        force=args.force,
    )


if __name__ == "__main__":
    main()