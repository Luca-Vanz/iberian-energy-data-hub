import json
from pathlib import Path

import pandas as pd


RAW_DIR = (
    Path("data")
    / "raw"
    / "esios"
    / "balancing"
    / "afrr_capacity_down_marginal"
)

INDICATOR_ID = 634

QH_GENERAL_START = "20220524"


def main():

    timestamps = []

    files = sorted(
        RAW_DIR.glob(
            f"{INDICATOR_ID}_*.json"
        )
    )

    for path in files:

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        values = (
            payload
            .get("indicator", {})
            .get("values", [])
            or []
        )

        for observation in values:

            dt = (
                observation.get("datetime_utc")
                or observation.get("datetime")
            )

            if dt is None:

                continue

            timestamp_utc = pd.Timestamp(
                dt
            )

            if timestamp_utc.tzinfo is None:

                timestamp_utc = (
                    timestamp_utc
                    .tz_localize("UTC")
                )

            else:

                timestamp_utc = (
                    timestamp_utc
                    .tz_convert("UTC")
                )

            timestamp_market = (
                timestamp_utc
                .tz_convert(
                    "Europe/Madrid"
                )
            )

            market_date = (
                timestamp_market
                .strftime("%Y%m%d")
            )

            if (
                market_date
                < QH_GENERAL_START
            ):

                timestamps.append(
                    timestamp_market
                )

    qh_dates = sorted(
        {
            timestamp.strftime(
                "%Y%m%d"
            )
            for timestamp in timestamps
            if timestamp.minute in {
                15,
                30,
                45,
            }
        }
    )

    print("=" * 80)

    print(
        "PRE-24-MAY-2022 QUARTER-HOUR "
        "OBSERVATIONS — ESIOS 634"
    )

    print("=" * 80)

    print(
        f"Dates found: "
        f"{len(qh_dates)}"
    )

    for market_date in qh_dates:

        print()
        print(
            f"DATE {market_date}"
        )

        day_values = [
            timestamp
            for timestamp in timestamps
            if timestamp.strftime(
                "%Y%m%d"
            ) == market_date
        ]

        for timestamp in day_values:

            print(
                f"  "
                f"{timestamp.isoformat()}"
            )

    print()
    print("=" * 80)


if __name__ == "__main__":

    main()