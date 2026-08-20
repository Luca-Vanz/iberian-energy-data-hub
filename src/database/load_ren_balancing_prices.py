from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from src.config import IS_PUBLIC
from src.database.connection import (
    get_database_connection,
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


# ==================================================
# REN SERIES
#
# Only datasets successfully retrieved from
# REN's live web service are loaded.
#
# GetSecResPrice is deliberately excluded because
# REN currently returns:
#
# INPUT05 | Unknown Type "GetSecResPrice!"
# ==================================================

SERIES = {

    "afrr_energy": {
        "info_type":
            "GetSecRegEnerPrice",

        "service":
            "afrr",
    },

    "afrr_capacity": {
        "info_type":
            "GetBaFRRPrice",

        "service":
            "afrr",
    },

    "mfrr_legacy_regulating_reserve": {
        "info_type":
            "GetRegResEnerPrice",

        "service":
            "mfrr",
    },

    "mfrr": {
        "info_type":
            "GetmFRRPrices",

        "service":
            "mfrr",
    },

    "rr_legacy": {
        "info_type":
            "GetRepResPrice",

        "service":
            "rr",
    },

    "rr": {
        "info_type":
            "GetRRPrice",

        "service":
            "rr",
    },
}


SOURCE_IDS = [
    "GetSecRegEnerPrice",
    "GetBaFRRPrice",
    "GetRegResEnerPrice",
    "GetmFRRPrices",
    "GetRepResPrice",
    "GetRRPrice",
]


# ==================================================
# DATABASE TABLE
# ==================================================

def create_balancing_table(
    connection,
) -> None:

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
            balancing_market_data
        (

            timestamp_utc TEXT NOT NULL,

            timestamp_market TEXT NOT NULL,

            market_date TEXT NOT NULL,

            period INTEGER NOT NULL,

            country TEXT NOT NULL,

            service TEXT NOT NULL,

            market_stage TEXT NOT NULL,

            metric TEXT NOT NULL,

            direction TEXT NOT NULL,

            value REAL NOT NULL,

            unit TEXT NOT NULL,

            resolution_minutes INTEGER NOT NULL,

            source TEXT NOT NULL,

            source_id TEXT NOT NULL,

            PRIMARY KEY (
                timestamp_utc,
                country,
                service,
                market_stage,
                metric,
                direction,
                source_id
            )
        );
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_balancing_market_query

        ON balancing_market_data (
            country,
            service,
            market_stage,
            metric,
            direction,
            market_date
        );
        """
    )


# ==================================================
# XML HELPERS
# ==================================================

def local_name(
    element: ET.Element,
) -> str:

    return (
        element.tag
        .split("}")[-1]
        .upper()
    )


def find_items(
    root: ET.Element,
) -> list[ET.Element]:

    return [
        element
        for element in root.iter()
        if local_name(element) == "ITEM"
    ]


def item_to_dict(
    item: ET.Element,
) -> dict[str, str | None]:

    result = {}

    for child in item:

        name = local_name(
            child
        )

        if (
            child.text is None
            or child.text.strip() == ""
        ):

            value = None

        else:

            value = child.text.strip()

        result[
            name
        ] = value

    return result


# ==================================================
# OPTIONAL NUMBER
# ==================================================

def parse_optional_number(
    value: str | None,
):

    if value is None:

        return None

    value = value.strip()

    if value == "":

        return None

    # Support both:
    #
    # 68.01
    # 68,01
    # 1.000,00

    if "," in value:

        if "." in value:

            value = (
                value
                .replace(".", "")
                .replace(",", ".")
            )

        else:

            value = value.replace(
                ",",
                ".",
            )

    try:

        return float(
            value
        )

    except ValueError as exc:

        raise ValueError(
            f"Invalid REN numeric "
            f"value: {value!r}"
        ) from exc


# ==================================================
# FILE DISCOVERY
# ==================================================

def discover_files(
    slug: str,
) -> list[Path]:

    directory = (
        RAW_DIR
        / slug
    )

    if not directory.exists():

        raise FileNotFoundError(
            f"Missing REN raw "
            f"directory: {directory}"
        )

    files = sorted(
        directory.glob(
            "*.xml"
        )
    )

    if not files:

        raise FileNotFoundError(
            f"No REN XML files "
            f"found for {slug}"
        )

    return files


# ==================================================
# READ RAW ITEMS
# ==================================================

def read_raw_items(
    slug: str,
) -> tuple[
    list[dict],
    int,
]:

    files = discover_files(
        slug
    )

    observations = []

    for path in files:

        text = path.read_text(
            encoding="utf-8"
        )

        root = ET.fromstring(
            text
        )

        items = find_items(
            root
        )

        for item in items:

            observation = item_to_dict(
                item
            )

            observation[
                "_source_file"
            ] = path.name

            observations.append(
                observation
            )

    return (
        observations,
        len(files),
    )


# ==================================================
# RESOLUTION
#
# We infer resolution from REN's PERIOD structure.
#
# Hourly:
#   normal day = 24
#   DST spring = 23
#   DST autumn = 25
#
# Quarter-hourly:
#   normal day = 96
#   DST spring = 92
#   DST autumn = 100
#
# Therefore max PERIOD > 25 means QH.
# ==================================================

def build_resolution_map(
    observations: list[dict],
) -> dict[str, int]:

    max_period_by_date = {}

    for observation in observations:

        market_day = observation.get(
            "MARKETDAY"
        )

        period_text = observation.get(
            "PERIOD"
        )

        if market_day is None:

            raise ValueError(
                "REN observation has "
                "no MARKETDAY."
            )

        if period_text is None:

            raise ValueError(
                "REN observation has "
                "no PERIOD."
            )

        period = int(
            period_text
        )

        current_max = (
            max_period_by_date.get(
                market_day,
                0,
            )
        )

        max_period_by_date[
            market_day
        ] = max(
            current_max,
            period,
        )

    resolution_map = {}

    for (
        market_day,
        max_period,
    ) in max_period_by_date.items():

        if max_period > 25:

            resolution = 15

        else:

            resolution = 60

        resolution_map[
            market_day
        ] = resolution

    return resolution_map


# ==================================================
# TIMESTAMP
#
# IMPORTANT:
#
# REN MARKETDAY follows the MIBEL market clock.
#
# Example from REN:
#
# MARKETDAY = 2008-07-01
# UTCDATE   = 2008-06-30T22:00Z
#
# Europe/Madrid:
#   2008-07-01 00:00 CEST
#
# Europe/Lisbon would instead give 23:00 on
# 30 June and would not match MARKETDAY.
#
# Therefore timestamp_market uses Europe/Madrid.
# ==================================================

def parse_timestamp(
    utc_value: str,
):

    timestamp_utc = pd.Timestamp(
        utc_value
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

    return (
        timestamp_utc,
        timestamp_market,
    )


# ==================================================
# COMMON DATABASE ROW
# ==================================================

def make_row(
    observation: dict,
    service: str,
    market_stage: str,
    metric: str,
    direction: str,
    value: float,
    unit: str,
    resolution: int,
    source_id: str,
) -> tuple:

    market_day = observation.get(
        "MARKETDAY"
    )

    period_text = observation.get(
        "PERIOD"
    )

    utc_value = observation.get(
        "UTCDATE"
    )

    if market_day is None:

        raise ValueError(
            "REN observation missing "
            "MARKETDAY."
        )

    if period_text is None:

        raise ValueError(
            "REN observation missing "
            "PERIOD."
        )

    if utc_value is None:

        raise ValueError(
            "REN observation missing "
            "UTCDATE."
        )

    period = int(
        period_text
    )

    (
        timestamp_utc,
        timestamp_market,
    ) = parse_timestamp(
        utc_value
    )

    market_date = (
        market_day.replace(
            "-",
            "",
        )
    )

    local_market_date = (
        timestamp_market
        .strftime("%Y%m%d")
    )

    # ==================================================
    # SOURCE CONSISTENCY
    # ==================================================

    if (
        local_market_date
        != market_date
    ):

        raise ValueError(
            "REN MARKETDAY / UTCDATE "
            "date mismatch: "
            f"MARKETDAY={market_day}, "
            f"UTCDATE={utc_value}, "
            f"MIBEL market time="
            f"{timestamp_market}"
        )

    # ==================================================
    # PERIOD / RESOLUTION BASIC CHECK
    # ==================================================

    if resolution == 60:

        if period > 25:

            raise ValueError(
                f"Hourly REN day has "
                f"invalid period {period}: "
                f"{market_day}"
            )

    elif resolution == 15:

        if period > 100:

            raise ValueError(
                f"Quarter-hour REN day "
                f"has invalid period "
                f"{period}: "
                f"{market_day}"
            )

    else:

        raise ValueError(
            f"Unexpected resolution: "
            f"{resolution}"
        )

    return (

        timestamp_utc.isoformat(),

        timestamp_market.isoformat(),

        market_date,

        period,

        "PT",

        service,

        market_stage,

        metric,

        direction,

        float(
            value
        ),

        unit,

        resolution,

        "REN",

        source_id,
    )


# ==================================================
# aFRR ENERGY
#
# REN:
#
# UPPRICE
# DOWNPRICE
#
# Unit: EUR/MWh
# ==================================================

def parse_afrr_energy(
    observations,
    resolution_map,
):

    rows = []

    missing_up = 0
    missing_down = 0

    for observation in observations:

        market_day = observation[
            "MARKETDAY"
        ]

        resolution = (
            resolution_map[
                market_day
            ]
        )

        up_price = (
            parse_optional_number(
                observation.get(
                    "UPPRICE"
                )
            )
        )

        down_price = (
            parse_optional_number(
                observation.get(
                    "DOWNPRICE"
                )
            )
        )

        if up_price is None:

            missing_up += 1

        else:

            rows.append(
                make_row(
                    observation=
                        observation,

                    service=
                        "afrr",

                    market_stage=
                        "energy",

                    metric=
                        "marginal_price",

                    direction=
                        "up",

                    value=
                        up_price,

                    unit=
                        "EUR/MWh",

                    resolution=
                        resolution,

                    source_id=
                        "GetSecRegEnerPrice",
                )
            )

        if down_price is None:

            missing_down += 1

        else:

            rows.append(
                make_row(
                    observation=
                        observation,

                    service=
                        "afrr",

                    market_stage=
                        "energy",

                    metric=
                        "marginal_price",

                    direction=
                        "down",

                    value=
                        down_price,

                    unit=
                        "EUR/MWh",

                    resolution=
                        resolution,

                    source_id=
                        "GetSecRegEnerPrice",
                )
            )

    return (
        rows,
        {
            "missing_up":
                missing_up,

            "missing_down":
                missing_down,
        },
    )


# ==================================================
# NEW aFRR CAPACITY
#
# REN fields:
#
# DIRECTION
# PRICE
# ADJPRICE
# FINALPRICE
#
# Unit: EUR/MW
# ==================================================

def parse_afrr_capacity(
    observations,
    resolution_map,
):

    rows = []

    missing_values = 0
    invalid_directions = 0

    fields = [

        (
            "PRICE",
            "marginal_price",
        ),

        (
            "ADJPRICE",
            "adjusted_price",
        ),

        (
            "FINALPRICE",
            "final_price",
        ),
    ]

    for observation in observations:

        market_day = observation[
            "MARKETDAY"
        ]

        resolution = (
            resolution_map[
                market_day
            ]
        )

        raw_direction = (
            observation.get(
                "DIRECTION"
            )
        )

        if raw_direction == "U":

            direction = "up"

        elif raw_direction == "D":

            direction = "down"

        else:

            invalid_directions += 1

            continue

        for (
            field_name,
            metric,
        ) in fields:

            value = (
                parse_optional_number(
                    observation.get(
                        field_name
                    )
                )
            )

            if value is None:

                missing_values += 1

                continue

            rows.append(
                make_row(
                    observation=
                        observation,

                    service=
                        "afrr",

                    market_stage=
                        "capacity",

                    metric=
                        metric,

                    direction=
                        direction,

                    value=
                        value,

                    unit=
                        "EUR/MW",

                    resolution=
                        resolution,

                    source_id=
                        "GetBaFRRPrice",
                )
            )

    return (
        rows,
        {
            "missing_values":
                missing_values,

            "invalid_directions":
                invalid_directions,
        },
    )


# ==================================================
# LEGACY mFRR / REGULATING RESERVE
#
# REN:
#
# UPPRICE
# DOWNPRICE
#
# Unit: EUR/MWh
# ==================================================

def parse_mfrr_legacy(
    observations,
    resolution_map,
):

    rows = []

    missing_up = 0
    missing_down = 0

    for observation in observations:

        market_day = observation[
            "MARKETDAY"
        ]

        resolution = (
            resolution_map[
                market_day
            ]
        )

        up_price = (
            parse_optional_number(
                observation.get(
                    "UPPRICE"
                )
            )
        )

        down_price = (
            parse_optional_number(
                observation.get(
                    "DOWNPRICE"
                )
            )
        )

        if up_price is None:

            missing_up += 1

        else:

            rows.append(
                make_row(
                    observation=
                        observation,

                    service=
                        "mfrr",

                    market_stage=
                        "energy_scheduled_legacy",

                    metric=
                        "marginal_price",

                    direction=
                        "up",

                    value=
                        up_price,

                    unit=
                        "EUR/MWh",

                    resolution=
                        resolution,

                    source_id=
                        "GetRegResEnerPrice",
                )
            )

        if down_price is None:

            missing_down += 1

        else:

            rows.append(
                make_row(
                    observation=
                        observation,

                    service=
                        "mfrr",

                    market_stage=
                        "energy_scheduled_legacy",

                    metric=
                        "marginal_price",

                    direction=
                        "down",

                    value=
                        down_price,

                    unit=
                        "EUR/MWh",

                    resolution=
                        resolution,

                    source_id=
                        "GetRegResEnerPrice",
                )
            )

    return (
        rows,
        {
            "missing_up":
                missing_up,

            "missing_down":
                missing_down,
        },
    )


# ==================================================
# MODERN mFRR
#
# REN:
#
# SAPRICEUP
# SAPRICEDOWN
#
# DAPRICEQTUP
# DAPRICEQTDOWN
#
# DAPRICEQ1TUP
# DAPRICEQ1TDOWN
#
# We preserve all three activation concepts.
# ==================================================

def parse_mfrr(
    observations,
    resolution_map,
):

    rows = []

    missing_values = 0

    fields = [

        # ------------------------------------------
        # Scheduled activation
        # ------------------------------------------

        (
            "SAPRICEUP",
            "energy_scheduled",
            "scheduled_activation_price",
            "up",
        ),

        (
            "SAPRICEDOWN",
            "energy_scheduled",
            "scheduled_activation_price",
            "down",
        ),

        # ------------------------------------------
        # Direct activation Qt
        # ------------------------------------------

        (
            "DAPRICEQTUP",
            "energy_direct_qt",
            "direct_activation_price",
            "up",
        ),

        (
            "DAPRICEQTDOWN",
            "energy_direct_qt",
            "direct_activation_price",
            "down",
        ),

        # ------------------------------------------
        # Direct activation Q1t
        # ------------------------------------------

        (
            "DAPRICEQ1TUP",
            "energy_direct_q1t",
            "direct_activation_price",
            "up",
        ),

        (
            "DAPRICEQ1TDOWN",
            "energy_direct_q1t",
            "direct_activation_price",
            "down",
        ),
    ]

    for observation in observations:

        market_day = observation[
            "MARKETDAY"
        ]

        resolution = (
            resolution_map[
                market_day
            ]
        )

        for (
            field_name,
            market_stage,
            metric,
            direction,
        ) in fields:

            value = (
                parse_optional_number(
                    observation.get(
                        field_name
                    )
                )
            )

            if value is None:

                missing_values += 1

                continue

            rows.append(
                make_row(
                    observation=
                        observation,

                    service=
                        "mfrr",

                    market_stage=
                        market_stage,

                    metric=
                        metric,

                    direction=
                        direction,

                    value=
                        value,

                    unit=
                        "EUR/MWh",

                    resolution=
                        resolution,

                    source_id=
                        "GetmFRRPrices",
                )
            )

    return (
        rows,
        {
            "missing_values":
                missing_values,
        },
    )


# ==================================================
# RR
# ==================================================

def parse_rr(
    observations,
    resolution_map,
    source_id,
    legacy,
):

    rows = []

    missing_price = 0

    market_stage = (
        "energy_legacy"
        if legacy
        else "energy"
    )

    for observation in observations:

        market_day = observation[
            "MARKETDAY"
        ]

        resolution = (
            resolution_map[
                market_day
            ]
        )

        price = (
            parse_optional_number(
                observation.get(
                    "PRICE"
                )
            )
        )

        if price is None:

            missing_price += 1

            continue

        rows.append(
            make_row(
                observation=
                    observation,

                service=
                    "rr",

                market_stage=
                    market_stage,

                metric=
                    "activation_price",

                direction=
                    "none",

                value=
                    price,

                unit=
                    "EUR/MWh",

                resolution=
                    resolution,

                source_id=
                    source_id,
            )
        )

    return (
        rows,
        {
            "missing_price":
                missing_price,
        },
    )


# ==================================================
# PARSE ONE SERIES
# ==================================================

def parse_series(
    slug,
    observations,
    resolution_map,
):

    if slug == "afrr_energy":

        return parse_afrr_energy(
            observations,
            resolution_map,
        )

    if slug == "afrr_capacity":

        return parse_afrr_capacity(
            observations,
            resolution_map,
        )

    if (
        slug
        == "mfrr_legacy_regulating_reserve"
    ):

        return parse_mfrr_legacy(
            observations,
            resolution_map,
        )

    if slug == "mfrr":

        return parse_mfrr(
            observations,
            resolution_map,
        )

    if slug == "rr_legacy":

        return parse_rr(
            observations=
                observations,

            resolution_map=
                resolution_map,

            source_id=
                "GetRepResPrice",

            legacy=
                True,
        )

    if slug == "rr":

        return parse_rr(
            observations=
                observations,

            resolution_map=
                resolution_map,

            source_id=
                "GetRRPrice",

            legacy=
                False,
        )

    raise ValueError(
        f"Unknown REN series: "
        f"{slug}"
    )


# ==================================================
# INSERT
# ==================================================

def insert_rows(
    connection,
    rows,
):

    if not rows:

        return

    connection.executemany(
        """
        INSERT OR REPLACE INTO
            balancing_market_data
        (

            timestamp_utc,
            timestamp_market,
            market_date,
            period,

            country,

            service,
            market_stage,
            metric,
            direction,

            value,
            unit,

            resolution_minutes,

            source,
            source_id
        )

        VALUES (
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?
        );
        """,
        rows,
    )


# ==================================================
# REPORT
# ==================================================

def report(
    connection,
    series_stats,
):

    placeholders = ",".join(
        "?"
        for _ in SOURCE_IDS
    )

    expected_total = sum(
        stats[
            "database_rows"
        ]
        for stats
        in series_stats.values()
    )

    actual_total = (
        connection.execute(
            f"""
            SELECT COUNT(*)

            FROM balancing_market_data

            WHERE country = 'PT'

              AND source = 'REN'

              AND source_id IN (
                  {placeholders}
              );
            """,
            SOURCE_IDS,
        ).fetchone()[0]
    )

    print()
    print("=" * 100)

    print(
        "REN BALANCING DATABASE "
        "LOAD SUMMARY"
    )

    print("=" * 100)

    for (
        slug,
        stats,
    ) in series_stats.items():

        print()

        print(
            slug
        )

        print(
            f"  Raw files: "
            f"{stats['files']:,}"
        )

        print(
            f"  Source items: "
            f"{stats['source_items']:,}"
        )

        print(
            f"  Database price rows: "
            f"{stats['database_rows']:,}"
        )

        print(
            f"  Hourly source items: "
            f"{stats['hourly_items']:,}"
        )

        print(
            f"  15-minute source items: "
            f"{stats['qh_items']:,}"
        )

        print(
            f"  First market date: "
            f"{stats['first_date']}"
        )

        print(
            f"  Last market date: "
            f"{stats['last_date']}"
        )

        for (
            key,
            value,
        ) in stats[
            "parser_stats"
        ].items():

            if isinstance(
                value,
                int,
            ):

                print(
                    f"  {key}: "
                    f"{value:,}"
                )

            else:

                print(
                    f"  {key}: "
                    f"{value}"
                )

    print()
    print("-" * 100)

    print(
        f"Expected total price rows: "
        f"{expected_total:,}"
    )

    print(
        f"Actual total price rows: "
        f"{actual_total:,}"
    )

    # ==================================================
    # ROWS BY RESOLUTION
    # ==================================================

    resolution_rows = (
        connection.execute(
            f"""
            SELECT
                resolution_minutes,
                COUNT(*)

            FROM balancing_market_data

            WHERE country = 'PT'

              AND source = 'REN'

              AND source_id IN (
                  {placeholders}
              )

            GROUP BY
                resolution_minutes

            ORDER BY
                resolution_minutes;
            """,
            SOURCE_IDS,
        ).fetchall()
    )

    print()

    print(
        "Database rows by resolution:"
    )

    for (
        resolution,
        count,
    ) in resolution_rows:

        print(
            f"  {resolution} min: "
            f"{count:,}"
        )

    # ==================================================
    # ROWS BY SERIES TYPE
    # ==================================================

    series_rows = (
        connection.execute(
            f"""
            SELECT
                service,
                market_stage,
                metric,
                direction,
                unit,
                COUNT(*)

            FROM balancing_market_data

            WHERE country = 'PT'

              AND source = 'REN'

              AND source_id IN (
                  {placeholders}
              )

            GROUP BY
                service,
                market_stage,
                metric,
                direction,
                unit

            ORDER BY
                service,
                market_stage,
                metric,
                direction;
            """,
            SOURCE_IDS,
        ).fetchall()
    )

    print()

    print(
        "Rows by series:"
    )

    for (
        service,
        stage,
        metric,
        direction,
        unit,
        count,
    ) in series_rows:

        print(
            f"  {service} | "
            f"{stage} | "
            f"{metric} | "
            f"{direction} | "
            f"{unit}: "
            f"{count:,}"
        )

    print()
    print("=" * 100)

    if (
        expected_total
        == actual_total
    ):

        print(
            "REN BALANCING LOAD "
            "CONSISTENCY PASSED"
        )

    else:

        print(
            "REN BALANCING LOAD "
            "CONSISTENCY FAILED"
        )

    print("=" * 100)


# ==================================================
# MAIN
# ==================================================

def main():

    if IS_PUBLIC:

        raise RuntimeError(
            "Do not load REN balancing "
            "data while "
            "IBERIAN_APP_MODE=public."
        )

    print("=" * 80)

    print(
        "LOADING PORTUGUESE REN "
        "BALANCING PRICES"
    )

    print("=" * 80)

    all_rows = []

    series_stats = {}

    # ==================================================
    # READ / PARSE ALL REN SERIES
    # ==================================================

    for slug in SERIES:

        print(
            f"Reading {slug}"
        )

        (
            observations,
            file_count,
        ) = read_raw_items(
            slug
        )

        resolution_map = (
            build_resolution_map(
                observations
            )
        )

        (
            rows,
            parser_stats,
        ) = parse_series(
            slug,
            observations,
            resolution_map,
        )

        all_rows.extend(
            rows
        )

        hourly_items = sum(
            1
            for observation
            in observations

            if (
                resolution_map[
                    observation[
                        "MARKETDAY"
                    ]
                ]
                == 60
            )
        )

        qh_items = (
            len(observations)
            - hourly_items
        )

        market_dates = [
            observation[
                "MARKETDAY"
            ]
            for observation
            in observations
        ]

        series_stats[
            slug
        ] = {

            "files":
                file_count,

            "source_items":
                len(
                    observations
                ),

            "database_rows":
                len(
                    rows
                ),

            "hourly_items":
                hourly_items,

            "qh_items":
                qh_items,

            "first_date":
                (
                    min(
                        market_dates
                    )
                    if market_dates
                    else None
                ),

            "last_date":
                (
                    max(
                        market_dates
                    )
                    if market_dates
                    else None
                ),

            "parser_stats":
                parser_stats,
        }

    # ==================================================
    # DATABASE LOAD
    # ==================================================

    with get_database_connection() as connection:

        create_balancing_table(
            connection
        )

        placeholders = ",".join(
            "?"
            for _ in SOURCE_IDS
        )

        # ==================================================
        # DELETE ONLY PORTUGUESE REN DATA MANAGED
        # BY THIS LOADER.
        #
        # Spanish ESIOS rows remain untouched.
        # ==================================================

        connection.execute(
            f"""
            DELETE FROM balancing_market_data

            WHERE country = 'PT'

              AND source = 'REN'

              AND source_id IN (
                  {placeholders}
              );
            """,
            SOURCE_IDS,
        )

        insert_rows(
            connection,
            all_rows,
        )

        connection.commit()

        report(
            connection=
                connection,

            series_stats=
                series_stats,
        )


if __name__ == "__main__":

    main()