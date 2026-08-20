from __future__ import annotations

import argparse
import html
import time
import xml.etree.ElementTree as ET

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import requests


# ==================================================
# REN SOAP SERVICE
# ==================================================

SOAP_ENDPOINT = (
    "https://ws-mercado.ren.pt/"
    "MarketInfoService.asmx"
)

SOAP_ACTION = (
    "https://ws-mercado.ren.pt/"
    "GetInfoForTimeFrameByInfoType"
)


# ==================================================
# PATHS
# ==================================================

RAW_DIR = (
    Path("data")
    / "raw"
    / "ren"
    / "balancing"
)

LOG_DIR = (
    Path("data")
    / "logs"
)


# ==================================================
# REQUEST LIMIT
#
# REN returned:
#
# INPUT03
# "Delta interval between input parameters
#  is bigger than 5 days."
#
# Therefore:
#
# start = 2026-08-14
# end   = 2026-08-19
#
# is accepted because the delta is exactly 5 days.
# ==================================================

MAX_DELTA_DAYS = 5


HISTORICAL_SCAN_START = "20070701"


# ==================================================
# SERIES CONFIGURATION
# ==================================================

@dataclass(frozen=True)
class SeriesConfig:

    slug: str

    info_type: str

    start_date: str

    end_date: str | None

    description: str


SERIES = [

    # ==================================================
    # aFRR ENERGY
    # ==================================================

    SeriesConfig(
        slug="afrr_energy",

        info_type="GetSecRegEnerPrice",

        start_date=
            HISTORICAL_SCAN_START,

        end_date=None,

        description=(
            "aFRR / secondary regulation "
            "energy marginal prices"
        ),
    ),

    # ==================================================
    # LEGACY aFRR CAPACITY
    # ==================================================

    SeriesConfig(
        slug="afrr_capacity_legacy",

        info_type="GetSecResPrice",

        start_date=
            HISTORICAL_SCAN_START,

        end_date="20260108",

        description=(
            "Legacy secondary reserve "
            "capacity marginal price"
        ),
    ),

    # ==================================================
    # CURRENT aFRR CAPACITY
    # ==================================================

    SeriesConfig(
        slug="afrr_capacity",

        info_type="GetBaFRRPrice",

        start_date="20260109",

        end_date=None,

        description=(
            "aFRR capacity prices "
            "under new market model"
        ),
    ),

    # ==================================================
    # LEGACY REGULATING RESERVE
    # ==================================================

    SeriesConfig(
        slug=(
            "mfrr_legacy_"
            "regulating_reserve"
        ),

        info_type="GetRegResEnerPrice",

        start_date=
            HISTORICAL_SCAN_START,

        end_date="20240313",

        description=(
            "Legacy regulating reserve "
            "energy prices"
        ),
    ),

    # ==================================================
    # mFRR
    # ==================================================

    SeriesConfig(
        slug="mfrr",

        info_type="GetmFRRPrices",

        start_date="20240314",

        end_date=None,

        description=(
            "mFRR scheduled and direct "
            "activation prices"
        ),
    ),

    # ==================================================
    # LEGACY RR
    # ==================================================

    SeriesConfig(
        slug="rr_legacy",

        info_type="GetRepResPrice",

        start_date="20201020",

        end_date="20250415",

        description=(
            "Legacy replacement reserve "
            "price"
        ),
    ),

    # ==================================================
    # RR
    # ==================================================

    SeriesConfig(
        slug="rr",

        info_type="GetRRPrice",

        start_date="20250416",

        end_date="20251230",

        description=(
            "Replacement Reserve "
            "activation price"
        ),
    ),
]


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


def iso_date(
    value: datetime,
) -> str:

    return value.strftime(
        "%Y-%m-%d"
    )


def compact_date(
    value: datetime,
) -> str:

    return value.strftime(
        "%Y%m%d"
    )


# ==================================================
# CHUNKS
#
# Delta must never exceed 5 days.
#
# Example:
#
# 1 Jan -> 6 Jan
#
# delta = 5 days
#
# Next request begins 7 Jan.
# ==================================================

def generate_chunks(
    start_date: str,
    end_date: str,
):

    current = parse_date(
        start_date
    )

    final = parse_date(
        end_date
    )

    while current <= final:

        chunk_end = min(
            current
            + timedelta(
                days=MAX_DELTA_DAYS
            ),
            final,
        )

        yield (
            current,
            chunk_end,
        )

        current = (
            chunk_end
            + timedelta(days=1)
        )


# ==================================================
# XML HELPERS
#
# REN is inconsistent in capitalization:
#
# MARKETDAY
# UTCDATE
# PRICE
#
# therefore all field lookup is
# case-insensitive.
# ==================================================

def local_name(
    element: ET.Element,
) -> str:

    return (
        element.tag
        .split("}")[-1]
        .upper()
    )


def find_descendant(
    root: ET.Element,
    name: str,
):

    expected = name.upper()

    for element in root.iter():

        if (
            local_name(element)
            == expected
        ):

            return element

    return None


def find_child_text(
    element: ET.Element,
    name: str,
) -> str | None:

    expected = name.upper()

    for child in element:

        if (
            local_name(child)
            == expected
        ):

            if child.text is None:

                return None

            return child.text.strip()

    return None


def find_items(
    root: ET.Element,
) -> list[ET.Element]:

    return [
        element
        for element in root.iter()
        if local_name(element)
        == "ITEM"
    ]


# ==================================================
# SOAP REQUEST
# ==================================================

def build_soap_body(
    start_day: datetime,
    end_day: datetime,
    info_type: str,
) -> str:

    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope
    xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
    xmlns:ws="https://ws-mercado.ren.pt">

    <soap:Header/>

    <soap:Body>

        <ws:GetInfoForTimeFrameByInfoType>

            <ws:StartDay>{iso_date(start_day)}</ws:StartDay>

            <ws:EndDay>{iso_date(end_day)}</ws:EndDay>

            <ws:InfoType>{info_type}</ws:InfoType>

        </ws:GetInfoForTimeFrameByInfoType>

    </soap:Body>

</soap:Envelope>
"""


# ==================================================
# EXTRACT INNER XML FROM SOAP ENVELOPE
# ==================================================

def extract_inner_xml(
    response_content: bytes,
) -> str:

    outer_root = ET.fromstring(
        response_content
    )

    result_element = None

    for element in outer_root.iter():

        if (
            local_name(element)
            == (
                "GETINFOFORTIMEFRAME"
                "BYINFOTYPERESULT"
            )
        ):

            result_element = element

            break

    if result_element is None:

        raise ValueError(
            "REN SOAP response does not "
            "contain the expected result."
        )

    result_text = (
        result_element.text
        or ""
    ).strip()

    if not result_text:

        raise ValueError(
            "REN SOAP response contains "
            "an empty result."
        )

    return html.unescape(
        result_text
    )


# ==================================================
# PARSE INNER REN RESPONSE
# ==================================================

def parse_inner_xml(
    inner_xml: str,
) -> dict:

    root = ET.fromstring(
        inner_xml
    )

    error_element = find_descendant(
        root,
        "ERROR",
    )

    if error_element is not None:

        code = find_child_text(
            error_element,
            "CODE",
        )

        message = find_child_text(
            error_element,
            "MESSAGE",
        )

        return {
            "status":
                "error",

            "error_code":
                (
                    code
                    if code
                    else "UNKNOWN"
                ),

            "error_message":
                (
                    message
                    if message
                    else ""
                ),

            "items":
                [],
        }

    items = find_items(
        root
    )

    return {
        "status":
            "ok",

        "error_code":
            None,

        "error_message":
            None,

        "items":
            items,
    }


# ==================================================
# REQUEST ONE CHUNK
# ==================================================

def request_chunk(
    http: requests.Session,
    info_type: str,
    start_day: datetime,
    end_day: datetime,
) -> dict:

    body = build_soap_body(
        start_day=
            start_day,

        end_day=
            end_day,

        info_type=
            info_type,
    )

    headers = {

        "Content-Type": (
            "application/soap+xml;"
            "charset=UTF-8;"
            f'action="{SOAP_ACTION}"'
        ),

        "Accept": (
            "application/soap+xml, "
            "text/xml"
        ),

        "User-Agent": (
            "iberian-energy-data-hub/1.0"
        ),
    }

    last_exception = None

    for attempt in range(
        1,
        4,
    ):

        try:

            response = http.post(
                SOAP_ENDPOINT,

                headers=headers,

                data=body.encode(
                    "utf-8"
                ),

                timeout=60,
            )

            response.raise_for_status()

            inner_xml = (
                extract_inner_xml(
                    response.content
                )
            )

            parsed = (
                parse_inner_xml(
                    inner_xml
                )
            )

            # Temporary general error:
            # retry before giving up.

            if (
                parsed["status"]
                == "error"

                and parsed[
                    "error_code"
                ] == "GEN01"

                and attempt < 3
            ):

                time.sleep(
                    attempt
                )

                continue

            return {
                **parsed,

                "inner_xml":
                    inner_xml,
            }

        except (
            requests.RequestException,
            ET.ParseError,
            ValueError,
        ) as exc:

            last_exception = exc

            if attempt == 3:

                raise

            time.sleep(
                attempt
            )

    raise RuntimeError(
        "Unexpected REN request failure."
    ) from last_exception


# ==================================================
# INSPECT SAVED FILE
# ==================================================

def inspect_saved_file(
    path: Path,
) -> tuple[
    int,
    str | None,
    str | None,
]:

    text = path.read_text(
        encoding="utf-8"
    )

    root = ET.fromstring(
        text
    )

    items = find_items(
        root
    )

    market_days = []

    for item in items:

        market_day = (
            find_child_text(
                item,
                "MARKETDAY",
            )
        )

        if market_day:

            market_days.append(
                market_day
            )

    return (
        len(items),

        (
            min(market_days)
            if market_days
            else None
        ),

        (
            max(market_days)
            if market_days
            else None
        ),
    )


# ==================================================
# OBSERVATION DATES FROM RESPONSE
# ==================================================

def get_market_days(
    items: list[ET.Element],
) -> list[str]:

    dates = []

    for item in items:

        market_day = (
            find_child_text(
                item,
                "MARKETDAY",
            )
        )

        if market_day:

            dates.append(
                market_day
            )

    return dates


# ==================================================
# DOWNLOAD ONE SERIES
# ==================================================

def download_series(
    config: SeriesConfig,
    requested_end: str,
    force: bool = False,
) -> dict:

    start_date = (
        config.start_date
    )

    end_date = (
        config.end_date
        if config.end_date
        is not None

        else requested_end
    )

    if end_date > requested_end:

        end_date = requested_end

    if end_date < start_date:

        return {
            "slug":
                config.slug,

            "info_type":
                config.info_type,

            "requests":
                0,

            "new_files":
                0,

            "existing_files":
                0,

            "no_data_chunks":
                0,

            "items":
                0,

            "errors":
                [],

            "first_observation":
                None,

            "last_observation":
                None,
        }

    output_dir = (
        RAW_DIR
        / config.slug
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    chunks = list(
        generate_chunks(
            start_date,
            end_date,
        )
    )

    print()
    print("=" * 75)

    print(
        config.slug
    )

    print(
        config.description
    )

    print(
        f"REN InfoType: "
        f"{config.info_type}"
    )

    print(
        f"Scan: "
        f"{start_date} -> "
        f"{end_date}"
    )

    print(
        f"Chunks: "
        f"{len(chunks)}"
    )

    print("=" * 75)

    requests_made = 0

    new_files = 0

    existing_files = 0

    no_data_chunks = 0

    total_items = 0

    first_observation = None

    last_observation = None

    errors = []

    with requests.Session() as http:

        for index, (
            chunk_start,
            chunk_end,
        ) in enumerate(
            chunks,
            start=1,
        ):

            start_compact = (
                compact_date(
                    chunk_start
                )
            )

            end_compact = (
                compact_date(
                    chunk_end
                )
            )

            output_path = (
                output_dir
                / (
                    f"{config.slug}_"
                    f"{start_compact}_"
                    f"{end_compact}.xml"
                )
            )

            # ==================================================
            # EXISTING FILE
            # ==================================================

            if (
                output_path.exists()
                and not force
            ):

                (
                    count,
                    first_date,
                    last_date,
                ) = inspect_saved_file(
                    output_path
                )

                existing_files += 1

                total_items += count

                if first_date:

                    if (
                        first_observation
                        is None

                        or first_date
                        < first_observation
                    ):

                        first_observation = (
                            first_date
                        )

                if last_date:

                    if (
                        last_observation
                        is None

                        or last_date
                        > last_observation
                    ):

                        last_observation = (
                            last_date
                        )

                continue

            # ==================================================
            # DOWNLOAD
            # ==================================================

            requests_made += 1

            try:

                result = request_chunk(
                    http=http,

                    info_type=
                        config.info_type,

                    start_day=
                        chunk_start,

                    end_day=
                        chunk_end,
                )

            except Exception as exc:

                errors.append(
                    (
                        start_compact,

                        end_compact,

                        type(exc).__name__,

                        str(exc),
                    )
                )

                continue

            # ==================================================
            # REN ERROR RESPONSE
            # ==================================================

            if (
                result["status"]
                == "error"
            ):

                code = (
                    result[
                        "error_code"
                    ]
                )

                # Official no-data response.

                if code == "GEN02":

                    no_data_chunks += 1

                    continue

                errors.append(
                    (
                        start_compact,

                        end_compact,

                        code,

                        result[
                            "error_message"
                        ],
                    )
                )

                continue

            items = (
                result["items"]
            )

            if not items:

                no_data_chunks += 1

                continue

            # ==================================================
            # SAVE RAW XML
            # ==================================================

            output_path.write_text(
                result[
                    "inner_xml"
                ],

                encoding="utf-8",
            )

            new_files += 1

            total_items += len(
                items
            )

            market_days = (
                get_market_days(
                    items
                )
            )

            if market_days:

                chunk_first = min(
                    market_days
                )

                chunk_last = max(
                    market_days
                )

                if (
                    first_observation
                    is None

                    or chunk_first
                    < first_observation
                ):

                    first_observation = (
                        chunk_first
                    )

                if (
                    last_observation
                    is None

                    or chunk_last
                    > last_observation
                ):

                    last_observation = (
                        chunk_last
                    )

            # ==================================================
            # PROGRESS
            # ==================================================

            if (
                index == 1

                or index % 100 == 0

                or index
                == len(chunks)
            ):

                print(
                    f"[{index}/"
                    f"{len(chunks)}] "
                    f"{start_compact}-"
                    f"{end_compact} "
                    f"| observations: "
                    f"{total_items:,}"
                )

            # Avoid hammering REN.

            time.sleep(
                0.05
            )

    return {

        "slug":
            config.slug,

        "info_type":
            config.info_type,

        "requests":
            requests_made,

        "new_files":
            new_files,

        "existing_files":
            existing_files,

        "no_data_chunks":
            no_data_chunks,

        "items":
            total_items,

        "errors":
            errors,

        "first_observation":
            first_observation,

        "last_observation":
            last_observation,
    }


# ==================================================
# ERROR LOG
# ==================================================

def write_error_log(
    summaries: list[dict],
) -> None:

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        LOG_DIR
        / "ren_balancing_price_errors.txt"
    )

    lines = []

    for summary in summaries:

        for (
            start_date,
            end_date,
            error_type,
            message,
        ) in summary[
            "errors"
        ]:

            lines.append(
                (
                    f"{summary['slug']} | "
                    f"{summary['info_type']} | "
                    f"{start_date} | "
                    f"{end_date} | "
                    f"{error_type} | "
                    f"{message}"
                )
            )

    if lines:

        path.write_text(
            "\n".join(
                lines
            ),

            encoding="utf-8",
        )

    elif path.exists():

        path.unlink()


# ==================================================
# DOWNLOAD ALL
# ==================================================

def download_all(
    end_date: str,
    force: bool = False,
) -> None:

    summaries = []

    for config in SERIES:

        summary = (
            download_series(
                config=config,

                requested_end=
                    end_date,

                force=
                    force,
            )
        )

        summaries.append(
            summary
        )

    write_error_log(
        summaries
    )

    print()
    print("=" * 90)

    print(
        "REN BALANCING PRICE "
        "DOWNLOAD SUMMARY"
    )

    print("=" * 90)

    for summary in summaries:

        print()

        print(
            summary["slug"]
        )

        print(
            f"  InfoType: "
            f"{summary['info_type']}"
        )

        print(
            f"  Observations: "
            f"{summary['items']:,}"
        )

        print(
            f"  First observation: "
            f"{summary['first_observation']}"
        )

        print(
            f"  Last observation: "
            f"{summary['last_observation']}"
        )

        print(
            f"  New raw files: "
            f"{summary['new_files']}"
        )

        print(
            f"  Existing raw files: "
            f"{summary['existing_files']}"
        )

        print(
            f"  No-data chunks: "
            f"{summary['no_data_chunks']}"
        )

        print(
            f"  Errors: "
            f"{len(summary['errors'])}"
        )

    total_errors = sum(
        len(
            summary[
                "errors"
            ]
        )
        for summary in summaries
    )

    print()
    print("-" * 90)

    print(
        f"Total errors: "
        f"{total_errors}"
    )

    if total_errors:

        print(
            "See "
            "data/logs/"
            "ren_balancing_price_errors.txt"
        )

    print("=" * 90)


# ==================================================
# CLI
# ==================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Download historical "
            "Portuguese balancing prices "
            "from REN."
        )
    )

    parser.add_argument(
        "--end",

        default="20260819",

        help=(
            "Final market date in "
            "YYYYMMDD format."
        ),
    )

    parser.add_argument(
        "--force",

        action="store_true",

        help=(
            "Redownload existing raw XML."
        ),
    )

    args = parser.parse_args()

    parse_date(
        args.end
    )

    download_all(
        end_date=
            args.end,

        force=
            args.force,
    )


if __name__ == "__main__":

    main()