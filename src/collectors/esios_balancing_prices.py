from __future__ import annotations

import argparse
import json
import os
import time
from calendar import monthrange
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()


BASE_URL = "https://api.esios.ree.es"

API_KEY = os.getenv(
    "ESIOS_API_KEY"
)


RAW_DIR = (
    Path("data")
    / "raw"
    / "esios"
    / "balancing"
)


DEFAULT_REQUEST_PAUSE_SECONDS = 1.0
MAX_ATTEMPTS = 5


class TemporaryApiBlockError(RuntimeError):
    """ESIOS temporarily rejected the request pattern."""


# ==================================================
# INDICATORS
#
# We deliberately download overlapping old/new
# series. We will determine their exact real
# start/end dates from the observations rather
# than hard-coding a transition.
# ==================================================

INDICATORS = {

    # --------------------------------------------------
    # aFRR ENERGY
    # --------------------------------------------------

    682: {
        "slug":
            "afrr_energy_up_marginal",

        "service":
            "afrr",

        "market_stage":
            "energy",

        "direction":
            "up",
    },

    683: {
        "slug":
            "afrr_energy_down_marginal",

        "service":
            "afrr",

        "market_stage":
            "energy",

        "direction":
            "down",
    },

    # --------------------------------------------------
    # aFRR CAPACITY
    #
    # Weighted-average reserve price series provide
    # useful historical continuity.
    # --------------------------------------------------

    10388: {
        "slug":
            "afrr_capacity_up_weighted",

        "service":
            "afrr",

        "market_stage":
            "capacity",

        "direction":
            "up",
    },

    10463: {
        "slug":
            "afrr_capacity_down_weighted",

        "service":
            "afrr",

        "market_stage":
            "capacity",

        "direction":
            "down",
    },

    # Marginal capacity-price indicators.
    # We retain them separately rather than
    # pretending they have exactly the same
    # historical definition as the weighted series.

    2130: {
        "slug":
            "afrr_capacity_up_marginal",

        "service":
            "afrr",

        "market_stage":
            "capacity",

        "direction":
            "up",
    },

    634: {
        "slug":
            "afrr_capacity_down_marginal",

        "service":
            "afrr",

        "market_stage":
            "capacity",

        "direction":
            "down",
    },

    # --------------------------------------------------
    # LEGACY mFRR / TERTIARY REGULATION
    # --------------------------------------------------

    677: {
        "slug":
            "mfrr_legacy_scheduled_up_marginal",

        "service":
            "mfrr",

        "market_stage":
            "energy",

        "direction":
            "up",
    },

    676: {
        "slug":
            "mfrr_legacy_scheduled_down_marginal",

        "service":
            "mfrr",

        "market_stage":
            "energy",

        "direction":
            "down",
    },

    # --------------------------------------------------
    # MODERN mFRR - SCHEDULED ACTIVATION
    # --------------------------------------------------

    10398: {
        "slug":
            "mfrr_scheduled_up_weighted",

        "service":
            "mfrr",

        "market_stage":
            "energy_scheduled",

        "direction":
            "up",
    },

    10399: {
        "slug":
            "mfrr_scheduled_down_weighted",

        "service":
            "mfrr",

        "market_stage":
            "energy_scheduled",

        "direction":
            "down",
    },

    # --------------------------------------------------
    # MODERN mFRR - DIRECT ACTIVATION
    # --------------------------------------------------

    10400: {
        "slug":
            "mfrr_direct_up_weighted",

        "service":
            "mfrr",

        "market_stage":
            "energy_direct",

        "direction":
            "up",
    },

    10401: {
        "slug":
            "mfrr_direct_down_weighted",

        "service":
            "mfrr",

        "market_stage":
            "energy_direct",

        "direction":
            "down",
    },

    # --------------------------------------------------
    # MODERN mFRR COMMON SCHEDULED PRICE
    #
    # Useful as a cross-check but not the main
    # UP/DOWN dashboard series.
    # --------------------------------------------------

    2197: {
        "slug":
            "mfrr_scheduled_price",

        "service":
            "mfrr",

        "market_stage":
            "energy_scheduled",

        "direction":
            "none",
    },

    # Replacement reserve (RR) marginal energy price.
    # ESIOS indicator 1782 covers the Spanish system and ends
    # with the final published observation on 30 December 2025.
    1782: {
        "slug":
            "rr_energy_marginal",

        "service":
            "rr",

        "market_stage":
            "energy",

        "direction":
            "none",

        "last_date":
            "20251230",
    },
}


START_DATE = "20180101"


# ==================================================
# HEADERS
# ==================================================

def get_headers() -> dict:

    if not API_KEY:

        raise RuntimeError(
            "ESIOS_API_KEY environment "
            "variable is not set."
        )

    return {
        "Accept": (
            "application/json; "
            "application/"
            "vnd.esios-api-v1+json"
        ),

        "Content-Type":
            "application/json",

        "x-api-key":
            API_KEY,

        "User-Agent":
            "iberian-energy-data-hub/1.0",
    }


# ==================================================
# DATE HELPERS
# ==================================================

def parse_date(
    value: str,
) -> datetime:

    return datetime.strptime(
        value,
        "%Y%m%d",
    )


def month_chunks(
    start_date: str,
    end_date: str,
):

    current = parse_date(
        start_date
    )

    final = parse_date(
        end_date
    )

    current = current.replace(
        day=1
    )

    while current <= final:

        last_day = monthrange(
            current.year,
            current.month,
        )[1]

        chunk_start = max(
            current,
            parse_date(
                start_date
            ),
        )

        chunk_end = current.replace(
            day=last_day
        )

        chunk_end = min(
            chunk_end,
            final,
        )

        yield (
            chunk_start,
            chunk_end,
        )

        if current.month == 12:

            current = current.replace(
                year=current.year + 1,
                month=1,
                day=1,
            )

        else:

            current = current.replace(
                month=current.month + 1,
                day=1,
            )


def api_datetime_start(
    value: datetime,
) -> str:

    return value.strftime(
        "%Y-%m-%dT00:00:00Z"
    )


def api_datetime_end(
    value: datetime,
) -> str:

    return value.strftime(
        "%Y-%m-%dT23:59:59Z"
    )


# ==================================================
# REQUEST ONE MONTH
# ==================================================

def request_indicator_chunk(
    http: requests.Session,
    indicator_id: int,
    start_date: datetime,
    end_date: datetime,
) -> dict:

    url = (
        f"{BASE_URL}/indicators/"
        f"{indicator_id}"
    )

    params = {
        "start_date":
            api_datetime_start(
                start_date
            ),

        "end_date":
            api_datetime_end(
                end_date
            ),

        "locale":
            "es",
    }

    last_exception = None

    for attempt in range(1, MAX_ATTEMPTS + 1):

        try:

            response = http.get(
                url,
                headers=get_headers(),
                params=params,
                timeout=60,
            )

            if response.status_code == 403:
                raise TemporaryApiBlockError(
                    "ESIOS temporarily blocked the request. "
                    "Stop this indicator and resume after a cool-down."
                )

            if response.status_code == 429 or response.status_code >= 500:
                if attempt == MAX_ATTEMPTS:
                    response.raise_for_status()

                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(
                    60.0, 5.0 * (2 ** (attempt - 1))
                )
                time.sleep(delay)
                continue

            response.raise_for_status()

            return response.json()

        except TemporaryApiBlockError:
            raise

        except (
            requests.RequestException,
            ValueError,
        ) as exc:

            last_exception = exc

            if attempt == MAX_ATTEMPTS:

                raise

            time.sleep(min(60.0, 5.0 * (2 ** (attempt - 1))))

    raise RuntimeError(
        "Unexpected ESIOS request failure."
    ) from last_exception


# ==================================================
# GET VALUES
# ==================================================

def get_values(
    payload: dict,
) -> list[dict]:

    indicator = payload.get(
        "indicator",
        {}
    )

    values = indicator.get(
        "values",
        [],
    )

    if values is None:

        return []

    return values


# ==================================================
# DATETIME EXTRACTION
# ==================================================

def get_datetime(
    value: dict,
) -> str | None:

    return (
        value.get(
            "datetime_utc"
        )
        or value.get(
            "datetime"
        )
    )


# ==================================================
# DOWNLOAD INDICATOR
# ==================================================

def download_indicator(
    http: requests.Session,
    indicator_id: int,
    config: dict,
    end_date: str,
    force: bool,
    request_pause_seconds: float,
) -> dict:

    slug = config[
        "slug"
    ]

    output_dir = (
        RAW_DIR
        / slug
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    indicator_end_date = min(
        end_date,
        config.get("last_date", end_date),
    )

    chunks = list(
        month_chunks(
            START_DATE,
            indicator_end_date,
        )
    )

    total_values = 0

    first_observation = None
    last_observation = None

    new_files = 0
    existing_files = 0
    empty_chunks = 0
    errors = []

    print()
    print("=" * 78)

    print(
        f"{indicator_id} | "
        f"{slug}"
    )

    print("=" * 78)

    for index, (
        chunk_start,
        chunk_end,
    ) in enumerate(
        chunks,
        start=1,
    ):

        start_compact = (
            chunk_start.strftime(
                "%Y%m%d"
            )
        )

        end_compact = (
            chunk_end.strftime(
                "%Y%m%d"
            )
        )

        output_path = (
            output_dir
            / (
                f"{indicator_id}_"
                f"{start_compact}_"
                f"{end_compact}.json"
            )
        )

        # ----------------------------------------------
        # EXISTING RAW FILE
        # ----------------------------------------------

        if (
            output_path.exists()
            and not force
        ):

            try:

                payload = json.loads(
                    output_path.read_text(
                        encoding="utf-8"
                    )
                )

                values = get_values(
                    payload
                )

            except Exception as exc:

                errors.append(
                    (
                        start_compact,
                        end_compact,
                        (
                            "ExistingFileError: "
                            f"{exc}"
                        ),
                    )
                )

                continue

            existing_files += 1

        else:

            # ------------------------------------------
            # DOWNLOAD
            # ------------------------------------------

            try:

                payload = (
                    request_indicator_chunk(
                        http=http,
                        indicator_id=
                            indicator_id,
                        start_date=
                            chunk_start,
                        end_date=
                            chunk_end,
                    )
                )

            except TemporaryApiBlockError as exc:
                errors.append(
                    (start_compact, end_compact, str(exc))
                )
                print(
                    "Temporary ESIOS block detected; "
                    "stopping this indicator without further requests."
                )
                break

            except Exception as exc:

                errors.append(
                    (
                        start_compact,
                        end_compact,
                        (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                    )
                )

                continue

            values = get_values(
                payload
            )

            # Save successful API response even if
            # the values list is empty. That preserves
            # evidence that we checked this period.

            output_path.write_text(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            new_files += 1

            time.sleep(request_pause_seconds)

        # ----------------------------------------------
        # SUMMARY
        # ----------------------------------------------

        if not values:

            empty_chunks += 1

            continue

        total_values += len(
            values
        )

        datetimes = [
            get_datetime(
                value
            )
            for value in values
        ]

        datetimes = [
            value
            for value in datetimes
            if value is not None
        ]

        if datetimes:

            chunk_first = min(
                datetimes
            )

            chunk_last = max(
                datetimes
            )

            if (
                first_observation is None
                or chunk_first
                < first_observation
            ):

                first_observation = (
                    chunk_first
                )

            if (
                last_observation is None
                or chunk_last
                > last_observation
            ):

                last_observation = (
                    chunk_last
                )

        if (
            index == 1
            or index % 25 == 0
            or index == len(chunks)
        ):

            print(
                f"[{index}/"
                f"{len(chunks)}] "
                f"values so far: "
                f"{total_values:,}"
            )

    return {
        "indicator_id":
            indicator_id,

        "slug":
            slug,

        "service":
            config[
                "service"
            ],

        "market_stage":
            config[
                "market_stage"
            ],

        "direction":
            config[
                "direction"
            ],

        "values":
            total_values,

        "first_observation":
            first_observation,

        "last_observation":
            last_observation,

        "new_files":
            new_files,

        "existing_files":
            existing_files,

        "empty_chunks":
            empty_chunks,

        "errors":
            errors,
    }


# ==================================================
# MAIN DOWNLOAD
# ==================================================

def download_all(
    end_date: str,
    force: bool = False,
    indicator_ids: set[int] | None = None,
    request_pause_seconds: float = DEFAULT_REQUEST_PAUSE_SECONDS,
) -> None:

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    summaries = []

    with requests.Session() as http:

        for (
            indicator_id,
            config,
        ) in INDICATORS.items():

            if indicator_ids and indicator_id not in indicator_ids:
                continue

            summary = (
                download_indicator(
                    http=http,
                    indicator_id=
                        indicator_id,
                    config=config,
                    end_date=end_date,
                    force=force,
                    request_pause_seconds=request_pause_seconds,
                )
            )

            summaries.append(
                summary
            )

    print()
    print("=" * 100)

    print(
        "ESIOS BALANCING PRICE DOWNLOAD SUMMARY"
    )

    print("=" * 100)

    for summary in summaries:

        print()

        print(
            f"{summary['indicator_id']} | "
            f"{summary['slug']}"
        )

        print(
            f"  Values: "
            f"{summary['values']:,}"
        )

        print(
            f"  First: "
            f"{summary['first_observation']}"
        )

        print(
            f"  Last: "
            f"{summary['last_observation']}"
        )

        print(
            f"  Empty months: "
            f"{summary['empty_chunks']}"
        )

        print(
            f"  Errors: "
            f"{len(summary['errors'])}"
        )

    # ==================================================
    # SAVE COMPACT SUMMARY
    # ==================================================

    summary_path = (
        RAW_DIR
        / "download_summary.json"
    )

    summary_path.write_text(
        json.dumps(
            summaries,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    total_errors = sum(
        len(
            item[
                "errors"
            ]
        )
        for item in summaries
    )

    print()
    print("-" * 100)

    print(
        f"Total errors: "
        f"{total_errors}"
    )

    print(
        f"Summary saved to: "
        f"{summary_path}"
    )

    print("=" * 100)


# ==================================================
# CLI
# ==================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Download Spanish aFRR and "
            "mFRR price history from ESIOS."
        )
    )

    parser.add_argument(
        "--end",
        default="20260819",
        help=(
            "Final date in YYYYMMDD format."
        ),
    )

    parser.add_argument(
        "--indicator",
        action="append",
        type=int,
        choices=sorted(INDICATORS),
        help=(
            "Download only this indicator. Repeat the option "
            "to select more than one indicator."
        ),
    )

    parser.add_argument(
        "--pause",
        type=float,
        default=DEFAULT_REQUEST_PAUSE_SECONDS,
        help="Seconds to wait after each successful API request.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Redownload existing monthly "
            "API responses."
        ),
    )

    args = parser.parse_args()

    parse_date(
        args.end
    )

    download_all(
        end_date=args.end,
        force=args.force,
        indicator_ids=(set(args.indicator) if args.indicator else None),
        request_pause_seconds=args.pause,
    )


if __name__ == "__main__":

    main()
