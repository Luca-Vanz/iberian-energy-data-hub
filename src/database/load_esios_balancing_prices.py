from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.config import IS_PUBLIC
from src.database.connection import get_database_connection


RAW_DIR = (
    Path("data")
    / "raw"
    / "esios"
    / "balancing"
)


# ==================================================
# OFFICIAL GENERAL QH TRANSITION
#
# Spanish balancing-system programming moved to
# quarter-hourly resolution on 24 May 2022.
#
# Before this date, unusual source-specific
# quarter-hour observations are detected from
# the actual ESIOS timestamps.
# ==================================================

QH_START_DATE = "20220524"


# ==================================================
# ESIOS INDICATORS
# ==================================================

INDICATORS = {

    # aFRR ENERGY

    682: {
        "slug": "afrr_energy_up_marginal",
        "service": "afrr",
        "market_stage": "energy",
        "metric": "marginal_price",
        "direction": "up",
        "unit": "EUR/MWh",
    },

    683: {
        "slug": "afrr_energy_down_marginal",
        "service": "afrr",
        "market_stage": "energy",
        "metric": "marginal_price",
        "direction": "down",
        "unit": "EUR/MWh",
    },

    # aFRR CAPACITY — WEIGHTED

    10388: {
        "slug": "afrr_capacity_up_weighted",
        "service": "afrr",
        "market_stage": "capacity",
        "metric": "weighted_average_price",
        "direction": "up",
        "unit": "EUR/MW",
    },

    10463: {
        "slug": "afrr_capacity_down_weighted",
        "service": "afrr",
        "market_stage": "capacity",
        "metric": "weighted_average_price",
        "direction": "down",
        "unit": "EUR/MW",
    },

    # aFRR CAPACITY — MARGINAL

    2130: {
        "slug": "afrr_capacity_up_marginal",
        "service": "afrr",
        "market_stage": "capacity",
        "metric": "marginal_price",
        "direction": "up",
        "unit": "EUR/MW",
    },

    634: {
        "slug": "afrr_capacity_down_marginal",
        "service": "afrr",
        "market_stage": "capacity",
        "metric": "marginal_price",
        "direction": "down",
        "unit": "EUR/MW",
    },

    # LEGACY mFRR / TERTIARY

    677: {
        "slug": "mfrr_legacy_scheduled_up_marginal",
        "service": "mfrr",
        "market_stage": "energy_scheduled_legacy",
        "metric": "marginal_price",
        "direction": "up",
        "unit": "EUR/MWh",
    },

    676: {
        "slug": "mfrr_legacy_scheduled_down_marginal",
        "service": "mfrr",
        "market_stage": "energy_scheduled_legacy",
        "metric": "marginal_price",
        "direction": "down",
        "unit": "EUR/MWh",
    },

    # mFRR SCHEDULED ACTIVATION

    10398: {
        "slug": "mfrr_scheduled_up_weighted",
        "service": "mfrr",
        "market_stage": "energy_scheduled",
        "metric": "weighted_average_price",
        "direction": "up",
        "unit": "EUR/MWh",
    },

    10399: {
        "slug": "mfrr_scheduled_down_weighted",
        "service": "mfrr",
        "market_stage": "energy_scheduled",
        "metric": "weighted_average_price",
        "direction": "down",
        "unit": "EUR/MWh",
    },

    # mFRR DIRECT ACTIVATION

    10400: {
        "slug": "mfrr_direct_up_weighted",
        "service": "mfrr",
        "market_stage": "energy_direct",
        "metric": "weighted_average_price",
        "direction": "up",
        "unit": "EUR/MWh",
    },

    10401: {
        "slug": "mfrr_direct_down_weighted",
        "service": "mfrr",
        "market_stage": "energy_direct",
        "metric": "weighted_average_price",
        "direction": "down",
        "unit": "EUR/MWh",
    },

    # mFRR MARI-ERA MARKET PRICE

    2197: {
        "slug": "mfrr_scheduled_price",
        "service": "mfrr",
        "market_stage": "energy_scheduled",
        "metric": "market_price",
        "direction": "none",
        "unit": "EUR/MWh",
    },
}


# ==================================================
# DATABASE
# ==================================================

def create_balancing_table(connection):

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS balancing_market_data (

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
# TIMESTAMPS
# ==================================================

def parse_timestamp(timestamp_value):

    timestamp_utc = pd.Timestamp(
        timestamp_value
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

    return (
        timestamp_utc,
        timestamp_market,
        market_date,
    )


# ==================================================
# PERIOD NUMBER
# ==================================================

def calculate_period(
    timestamp_market,
    resolution,
):

    market_date = (
        timestamp_market
        .strftime("%Y-%m-%d")
    )

    start = (
        pd.Timestamp(
            market_date
        )
        .tz_localize(
            "Europe/Madrid"
        )
    )

    end = (
        start
        + pd.DateOffset(days=1)
    )

    frequency = (
        "15min"
        if resolution == 15
        else "60min"
    )

    periods = pd.date_range(
        start=start,
        end=end,
        freq=frequency,
        inclusive="left",
    )

    position = int(
        periods.get_indexer(
            [timestamp_market]
        )[0]
    )

    if position == -1:

        raise ValueError(
            "Timestamp does not fall "
            "on expected grid: "
            f"{timestamp_market} "
            f"({resolution} min)"
        )

    return position + 1


# ==================================================
# VALUE HELPERS
# ==================================================

def get_value_datetime(observation):

    return (
        observation.get(
            "datetime_utc"
        )
        or observation.get(
            "datetime"
        )
    )


def get_numeric_value(observation):

    raw_value = observation.get(
        "value"
    )

    if raw_value is None:

        return None

    try:

        return float(
            raw_value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise ValueError(
            f"Invalid ESIOS value: "
            f"{raw_value!r}"
        ) from exc


# ==================================================
# RAW FILE DISCOVERY
# ==================================================

def discover_files(
    indicator_id,
    slug,
):

    directory = (
        RAW_DIR
        / slug
    )

    if not directory.exists():

        raise FileNotFoundError(
            f"Missing raw directory: "
            f"{directory}"
        )

    files = sorted(
        directory.glob(
            f"{indicator_id}_*.json"
        )
    )

    if not files:

        raise FileNotFoundError(
            f"No JSON files for "
            f"indicator {indicator_id}"
        )

    return files


# ==================================================
# IDENTIFY PRE-REFORM QH OBSERVATIONS
#
# Important:
#
# We classify individual observations,
# NOT entire days.
#
# Example found in ESIOS indicator 634:
#
# 00:00
# 00:15
# ...
# 05:45
# 06:00
# 07:00
# 08:00
# ...
#
# 00:00–06:00 belongs to a QH sequence.
# 07:00 onward returns to hourly cadence.
# ==================================================

def identify_pre_reform_qh_observations(
    observations,
):

    qh_timestamps = set()

    for index, observation in enumerate(
        observations
    ):

        market_date = observation[
            "market_date"
        ]

        if market_date >= QH_START_DATE:

            continue

        current = observation[
            "timestamp_market"
        ]

        current_key = (
            observation[
                "timestamp_utc"
            ].isoformat()
        )

        # ------------------------------------------
        # Explicit quarter-hour timestamps
        # ------------------------------------------

        if current.minute in {
            15,
            30,
            45,
        }:

            qh_timestamps.add(
                current_key
            )

        # ------------------------------------------
        # Is previous observation 15 minutes away?
        # ------------------------------------------

        if index > 0:

            previous_observation = (
                observations[
                    index - 1
                ]
            )

            previous = (
                previous_observation[
                    "timestamp_market"
                ]
            )

            same_market_date = (
                previous_observation[
                    "market_date"
                ]
                == market_date
            )

            delta_minutes = (
                (
                    current.tz_convert("UTC")
                    - previous.tz_convert("UTC")
                )
                .total_seconds()
                / 60
            )

            if (
                same_market_date
                and delta_minutes == 15
            ):

                qh_timestamps.add(
                    current_key
                )

        # ------------------------------------------
        # Is next observation 15 minutes away?
        # ------------------------------------------

        if index < len(
            observations
        ) - 1:

            next_observation = (
                observations[
                    index + 1
                ]
            )

            next_timestamp = (
                next_observation[
                    "timestamp_market"
                ]
            )

            same_market_date = (
                next_observation[
                    "market_date"
                ]
                == market_date
            )

            delta_minutes = (
                (
                    next_timestamp.tz_convert(
                        "UTC"
                    )
                    - current.tz_convert(
                        "UTC"
                    )
                )
                .total_seconds()
                / 60
            )

            if (
                same_market_date
                and delta_minutes == 15
            ):

                qh_timestamps.add(
                    current_key
                )

    return qh_timestamps


# ==================================================
# RESOLUTION FOR ONE OBSERVATION
# ==================================================

def determine_resolution(
    observation,
    pre_reform_qh_timestamps,
):

    market_date = observation[
        "market_date"
    ]

    # Official general QH regime.

    if market_date >= QH_START_DATE:

        return 15

    timestamp_key = (
        observation[
            "timestamp_utc"
        ].isoformat()
    )

    # Source-specific historical QH segment.

    if (
        timestamp_key
        in pre_reform_qh_timestamps
    ):

        return 15

    return 60


# ==================================================
# READ ONE INDICATOR
# ==================================================

def read_indicator(
    indicator_id,
    config,
):

    files = discover_files(
        indicator_id,
        config["slug"],
    )

    observations = []

    seen_timestamps = {}

    source_observations = 0
    null_values = 0
    exact_duplicates = 0

    # ==================================================
    # READ AND DEDUPLICATE
    # ==================================================

    for path in files:

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        indicator = payload.get(
            "indicator",
            {}
        )

        values = (
            indicator.get(
                "values",
                []
            )
            or []
        )

        for source_value in values:

            source_observations += 1

            datetime_value = (
                get_value_datetime(
                    source_value
                )
            )

            if datetime_value is None:

                raise ValueError(
                    "Missing datetime in "
                    f"{path.name}"
                )

            numeric_value = (
                get_numeric_value(
                    source_value
                )
            )

            if numeric_value is None:

                null_values += 1
                continue

            (
                timestamp_utc,
                timestamp_market,
                market_date,
            ) = parse_timestamp(
                datetime_value
            )

            key = (
                timestamp_utc.isoformat()
            )

            if key in seen_timestamps:

                previous_value = (
                    seen_timestamps[key]
                )

                if (
                    previous_value
                    != numeric_value
                ):

                    raise ValueError(
                        "Conflicting duplicate "
                        f"for indicator "
                        f"{indicator_id} at "
                        f"{key}: "
                        f"{previous_value} vs "
                        f"{numeric_value}"
                    )

                exact_duplicates += 1
                continue

            seen_timestamps[
                key
            ] = numeric_value

            observations.append(
                {
                    "timestamp_utc":
                        timestamp_utc,

                    "timestamp_market":
                        timestamp_market,

                    "market_date":
                        market_date,

                    "value":
                        numeric_value,
                }
            )

    # Chronological order is required for
    # interval-based resolution detection.

    observations.sort(
        key=lambda item:
            item[
                "timestamp_utc"
            ]
    )

    # ==================================================
    # FIND SOURCE-SPECIFIC PRE-REFORM QH SEGMENTS
    # ==================================================

    pre_reform_qh_timestamps = (
        identify_pre_reform_qh_observations(
            observations
        )
    )

    rows = []

    hourly_rows = 0
    quarter_hour_rows = 0

    pre_reform_qh_rows = 0

    resolutions_by_date = {}

    first_timestamp = None
    last_timestamp = None

    # ==================================================
    # BUILD DATABASE ROWS
    # ==================================================

    for observation in observations:

        resolution = (
            determine_resolution(
                observation,
                pre_reform_qh_timestamps,
            )
        )

        timestamp_market = (
            observation[
                "timestamp_market"
            ]
        )

        market_date = (
            observation[
                "market_date"
            ]
        )

        # ------------------------------------------
        # GRID VALIDATION
        # ------------------------------------------

        if resolution == 60:

            if (
                timestamp_market.minute
                != 0
            ):

                raise ValueError(
                    "Non-hourly timestamp "
                    "classified as hourly: "
                    f"{timestamp_market}"
                )

            hourly_rows += 1

        elif resolution == 15:

            if (
                timestamp_market.minute
                % 15
                != 0
            ):

                raise ValueError(
                    "Timestamp not on "
                    "15-minute grid: "
                    f"{timestamp_market}"
                )

            quarter_hour_rows += 1

            if (
                market_date
                < QH_START_DATE
            ):

                pre_reform_qh_rows += 1

        else:

            raise ValueError(
                f"Invalid resolution: "
                f"{resolution}"
            )

        resolutions_by_date.setdefault(
            market_date,
            set(),
        ).add(
            resolution
        )

        period = calculate_period(
            timestamp_market=
                timestamp_market,

            resolution=
                resolution,
        )

        timestamp_utc = observation[
            "timestamp_utc"
        ]

        rows.append(
            (
                timestamp_utc.isoformat(),
                timestamp_market.isoformat(),

                market_date,
                period,

                "ES",

                config["service"],
                config["market_stage"],
                config["metric"],
                config["direction"],

                observation["value"],
                config["unit"],

                resolution,

                "ESIOS",
                str(indicator_id),
            )
        )

        if (
            first_timestamp is None
            or timestamp_utc
            < first_timestamp
        ):

            first_timestamp = (
                timestamp_utc
            )

        if (
            last_timestamp is None
            or timestamp_utc
            > last_timestamp
        ):

            last_timestamp = (
                timestamp_utc
            )

    mixed_resolution_dates = sorted(
        market_date
        for (
            market_date,
            resolutions,
        ) in resolutions_by_date.items()
        if len(resolutions) > 1
    )

    stats = {

        "files":
            len(files),

        "source_observations":
            source_observations,

        "database_rows":
            len(rows),

        "null_values":
            null_values,

        "exact_duplicates":
            exact_duplicates,

        "hourly_rows":
            hourly_rows,

        "quarter_hour_rows":
            quarter_hour_rows,

        "pre_reform_qh_rows":
            pre_reform_qh_rows,

        "mixed_resolution_dates":
            mixed_resolution_dates,

        "first_timestamp":
            (
                first_timestamp.isoformat()
                if first_timestamp is not None
                else None
            ),

        "last_timestamp":
            (
                last_timestamp.isoformat()
                if last_timestamp is not None
                else None
            ),
    }

    return rows, stats


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
    indicator_stats,
):

    indicator_ids = [
        str(indicator_id)
        for indicator_id
        in INDICATORS
    ]

    placeholders = ",".join(
        "?"
        for _ in indicator_ids
    )

    expected_total = sum(
        stats["database_rows"]
        for stats
        in indicator_stats.values()
    )

    actual_total = (
        connection.execute(
            f"""
            SELECT COUNT(*)

            FROM balancing_market_data

            WHERE country = 'ES'
              AND source = 'ESIOS'
              AND source_id IN (
                  {placeholders}
              );
            """,
            indicator_ids,
        ).fetchone()[0]
    )

    print()
    print("=" * 100)

    print(
        "ESIOS BALANCING DATABASE LOAD SUMMARY"
    )

    print("=" * 100)

    for indicator_id, config in (
        INDICATORS.items()
    ):

        stats = indicator_stats[
            indicator_id
        ]

        db_count = (
            connection.execute(
                """
                SELECT COUNT(*)

                FROM balancing_market_data

                WHERE country = 'ES'
                  AND source = 'ESIOS'
                  AND source_id = ?;
                """,
                (
                    str(indicator_id),
                ),
            ).fetchone()[0]
        )

        print()
        print(
            f"{indicator_id} | "
            f"{config['slug']}"
        )

        print(
            "  Source observations: "
            f"{stats['source_observations']:,}"
        )

        print(
            "  Null values skipped: "
            f"{stats['null_values']:,}"
        )

        print(
            "  Exact duplicates removed: "
            f"{stats['exact_duplicates']:,}"
        )

        print(
            "  Hourly rows: "
            f"{stats['hourly_rows']:,}"
        )

        print(
            "  15-minute rows: "
            f"{stats['quarter_hour_rows']:,}"
        )

        print(
            "  Pre-reform QH rows: "
            f"{stats['pre_reform_qh_rows']:,}"
        )

        print(
            "  Mixed-resolution dates: "
            f"{len(stats['mixed_resolution_dates'])}"
        )

        if stats[
            "mixed_resolution_dates"
        ]:

            print(
                "    "
                + ", ".join(
                    stats[
                        "mixed_resolution_dates"
                    ]
                )
            )

        print(
            "  Expected DB rows: "
            f"{stats['database_rows']:,}"
        )

        print(
            "  Actual DB rows: "
            f"{db_count:,}"
        )

        print(
            "  First: "
            f"{stats['first_timestamp']}"
        )

        print(
            "  Last: "
            f"{stats['last_timestamp']}"
        )

    print()
    print("-" * 100)

    print(
        "Expected total rows: "
        f"{expected_total:,}"
    )

    print(
        "Actual total rows: "
        f"{actual_total:,}"
    )

    resolution_rows = (
        connection.execute(
            f"""
            SELECT
                resolution_minutes,
                COUNT(*)

            FROM balancing_market_data

            WHERE country = 'ES'
              AND source = 'ESIOS'
              AND source_id IN (
                  {placeholders}
              )

            GROUP BY
                resolution_minutes

            ORDER BY
                resolution_minutes;
            """,
            indicator_ids,
        ).fetchall()
    )

    print()
    print(
        "Rows by resolution:"
    )

    for resolution, count in (
        resolution_rows
    ):

        print(
            f"  {resolution} min: "
            f"{count:,}"
        )

    print()
    print("=" * 100)

    if expected_total == actual_total:

        print(
            "ESIOS BALANCING LOAD "
            "CONSISTENCY PASSED"
        )

    else:

        print(
            "ESIOS BALANCING LOAD "
            "CONSISTENCY FAILED"
        )

    print("=" * 100)


# ==================================================
# MAIN
# ==================================================

def main():

    if IS_PUBLIC:

        raise RuntimeError(
            "Do not load balancing data "
            "while "
            "IBERIAN_APP_MODE=public."
        )

    print("=" * 80)

    print(
        "LOADING SPANISH ESIOS "
        "BALANCING PRICES"
    )

    print("=" * 80)

    all_rows = []

    indicator_stats = {}

    for (
        indicator_id,
        config,
    ) in INDICATORS.items():

        print(
            f"Reading "
            f"{indicator_id} | "
            f"{config['slug']}"
        )

        rows, stats = read_indicator(
            indicator_id,
            config,
        )

        all_rows.extend(
            rows
        )

        indicator_stats[
            indicator_id
        ] = stats

    with get_database_connection() as connection:

        create_balancing_table(
            connection
        )

        indicator_ids = [
            str(indicator_id)
            for indicator_id
            in INDICATORS
        ]

        placeholders = ",".join(
            "?"
            for _ in indicator_ids
        )

        connection.execute(
            f"""
            DELETE FROM balancing_market_data

            WHERE country = 'ES'
              AND source = 'ESIOS'
              AND source_id IN (
                  {placeholders}
              );
            """,
            indicator_ids,
        )

        insert_rows(
            connection,
            all_rows,
        )

        connection.commit()

        report(
            connection,
            indicator_stats,
        )


if __name__ == "__main__":
    main()