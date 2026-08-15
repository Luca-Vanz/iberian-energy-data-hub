import argparse
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import requests


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


def download_ren_demand(
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


    # Keep the values directly inside the XML tags.
    # REN expects StartDay and EndDay as yyyy-mm-dd strings.
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


    response = requests.post(
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


    # Save the complete raw SOAP response
    output_path.write_bytes(
        response.content
    )


    print(
        f"Raw REN response saved to: "
        f"{output_path}"
    )


    # --------------------------------------------------
    # PARSE SOAP RESPONSE
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


    inner_xml = result_element.text.strip()


    inner_root = ET.fromstring(
        inner_xml
    )


    # --------------------------------------------------
    # CHECK FOR REN APPLICATION ERROR
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
    # INSPECT OBSERVATIONS
    # --------------------------------------------------

    items = inner_root.findall(
        ".//Item"
    )


    print()
    print(
        f"Observations returned: "
        f"{len(items)}"
    )


    if items:

        first_item = items[0]

        print()
        print(
            "First observation:"
        )


        for child in first_item:

            print(
                f"  {child.tag}: "
                f"{child.text}"
            )


        print()
        print(
            "Last observation:"
        )


        last_item = items[-1]


        for child in last_item:

            print(
                f"  {child.tag}: "
                f"{child.text}"
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


    args = parser.parse_args()


    download_ren_demand(
        date=args.date,
    )


if __name__ == "__main__":
    main()