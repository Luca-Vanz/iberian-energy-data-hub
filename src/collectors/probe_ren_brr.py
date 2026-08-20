from datetime import datetime

import requests

from src.collectors.ren_balancing_prices import (
    request_chunk,
    local_name,
)


PROBE_DATES = [
    "20180115",
    "20220115",
    "20230524",
    "20240315",
    "20250615",
    "20260108",
    "20260109",
]


def parse_date(value: str) -> datetime:

    return datetime.strptime(
        value,
        "%Y%m%d",
    )


def item_to_dict(item):

    result = {}

    for child in item:

        name = local_name(
            child
        )

        value = (
            child.text.strip()
            if child.text
            else None
        )

        result[name] = value

    return result


def main():

    print("=" * 80)
    print(
        "REN GetBrr PROBE"
    )
    print("=" * 80)

    with requests.Session() as http:

        for date_string in PROBE_DATES:

            day = parse_date(
                date_string
            )

            print()
            print(
                f"DATE {date_string}"
            )

            try:

                result = request_chunk(
                    http=http,
                    info_type="GetBrr",
                    start_day=day,
                    end_day=day,
                )

            except Exception as exc:

                print(
                    f"  REQUEST ERROR: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                continue

            if result["status"] == "error":

                print(
                    f"  REN ERROR: "
                    f"{result['error_code']} | "
                    f"{result['error_message']}"
                )

                continue

            items = result[
                "items"
            ]

            print(
                f"  Observations: "
                f"{len(items)}"
            )

            if not items:

                continue

            first = item_to_dict(
                items[0]
            )

            print(
                "  First observation:"
            )

            for name, value in (
                first.items()
            ):

                print(
                    f"    {name}: "
                    f"{value}"
                )

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()