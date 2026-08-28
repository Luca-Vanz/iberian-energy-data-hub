from __future__ import annotations

import argparse
import json
from datetime import timedelta

import pandas as pd

from src.database.connection import (
    get_database_connection,
)


# ==================================================
# SUPPORTED MARKETS
# ==================================================

WHOLESALE_MARKETS = {
    "day_ahead",
    "intraday_auction",
    "intraday_continuous",
}

BALANCING_MARKETS = {
    "afrr",
    "mfrr",
    "rr",
}

ALL_MARKETS = (
    WHOLESALE_MARKETS
    | BALANCING_MARKETS
)


# Dated product and resolution changes used as chart markers. These are
# fallback events so the storyline remains available for databases built
# before the corresponding rows were added to ``market_events``.
BUILTIN_MARKET_EVENTS = [
    {
        "event_date": "20180101", "country": "ES", "service": "afrr",
        "event_type": "coverage_start",
        "title": "aFRR historical indicator coverage begins",
        "description": "The validated ESIOS aFRR price history starts at hourly resolution.",
        "source": "ESIOS",
    },
    {
        "event_date": "20220524", "country": "ES", "service": "afrr",
        "event_type": "resolution_change",
        "title": "aFRR energy and weighted capacity series move to 15-minute data",
        "description": "The validated ESIOS series changes from hourly to quarter-hourly native observations.",
        "source": "ESIOS",
    },
    {
        "event_date": "20241120", "country": "ES", "service": "afrr",
        "event_type": "series_start",
        "title": "Upward aFRR capacity marginal series begins",
        "description": "This specific marginal capacity product starts later than the other aFRR indicators.",
        "source": "ESIOS",
    },
    {
        "event_date": "20180101", "country": "ES", "service": "mfrr",
        "event_type": "coverage_start",
        "title": "mFRR legacy price coverage begins",
        "description": "The validated legacy scheduled marginal-price history starts at hourly resolution.",
        "source": "ESIOS",
    },
    {
        "event_date": "20220524", "country": "ES", "service": "mfrr",
        "event_type": "resolution_change",
        "title": "mFRR weighted and legacy series move to 15-minute data",
        "description": "The validated ESIOS series changes from hourly to quarter-hourly native observations.",
        "source": "ESIOS",
    },
    {
        "event_date": "20220815", "country": "ES", "service": "mfrr",
        "event_type": "series_start",
        "title": "Direct downward mFRR series begins",
        "description": "The direct downward weighted-average product starts on this date.",
        "source": "ESIOS",
    },
    {
        "event_date": "20241210", "country": "ES", "service": "mfrr",
        "event_type": "market_redesign",
        "title": "mFRR scheduled market-price product replaces legacy marginal series",
        "description": "The current scheduled market-price product is kept separate from the legacy series.",
        "source": "ESIOS",
    },
]


# ==================================================
# DISPLAY FREQUENCIES
# ==================================================

FREQUENCY_ALIASES = {

    "15min": "15min",
    "15m": "15min",
    "15": "15min",

    "1h": "1h",
    "hour": "1h",
    "hourly": "1h",
    "60min": "1h",

    "daily": "daily",
    "day": "daily",
    "1d": "daily",

    "weekly": "weekly",
    "week": "weekly",
    "1w": "weekly",

    "monthly": "monthly",
    "month": "monthly",

    "yearly": "yearly",
    "annual": "yearly",
    "year": "yearly",
}


DISPLAY_MINUTES = {
    "15min": 15,
    "1h": 60,
    "daily": None,
    "weekly": None,
    "monthly": None,
    "yearly": None,
}


# ==================================================
# DATE HELPERS
# ==================================================

def normalize_date(
    value: str,
) -> str:

    value = value.strip()

    for fmt in [
        "%Y%m%d",
        "%Y-%m-%d",
    ]:

        try:

            timestamp = pd.to_datetime(
                value,
                format=fmt,
            )

            return timestamp.strftime(
                "%Y%m%d"
            )

        except ValueError:

            continue

    raise ValueError(
        f"Invalid date: {value}. "
        f"Use YYYYMMDD or YYYY-MM-DD."
    )


def readable_date(
    compact_date: str,
) -> str:

    return pd.to_datetime(
        compact_date,
        format="%Y%m%d",
    ).strftime(
        "%Y-%m-%d"
    )


# ==================================================
# COUNTRY
# ==================================================

def normalize_countries(
    country: str | list[str],
) -> list[str]:

    if isinstance(
        country,
        str,
    ):

        value = (
            country
            .strip()
            .upper()
        )

        if value == "BOTH":

            return [
                "ES",
                "PT",
            ]

        countries = [
            value
        ]

    else:

        countries = [
            value
            .strip()
            .upper()

            for value
            in country
        ]

    valid = {
        "ES",
        "PT",
    }

    invalid = [
        value
        for value
        in countries
        if value not in valid
    ]

    if invalid:

        raise ValueError(
            f"Invalid countries: "
            f"{invalid}. "
            f"Allowed: ES, PT, both."
        )

    return countries


# ==================================================
# FREQUENCY
# ==================================================

def normalize_frequency(
    frequency: str,
) -> str:

    key = (
        frequency
        .strip()
        .lower()
    )

    if key not in FREQUENCY_ALIASES:

        raise ValueError(
            f"Unsupported frequency: "
            f"{frequency}. "
            f"Use 15min, 1h, daily, "
            f"weekly, monthly or yearly."
        )

    return FREQUENCY_ALIASES[
        key
    ]


# ==================================================
# DATABASE TABLE CHECK
# ==================================================

def table_exists(
    connection,
    table_name: str,
) -> bool:

    row = connection.execute(
        """
        SELECT COUNT(*)

        FROM sqlite_master

        WHERE type = 'table'
          AND name = ?;
        """,
        (
            table_name,
        ),
    ).fetchone()

    return bool(
        row[0]
    )


# ==================================================
# MARKET PRICE QUERY
#
# OMIE:
#
# day_ahead
# intraday_auction
# intraday_continuous
# ==================================================

def load_wholesale_prices(
    connection,
    market: str,
    countries: list[str],
    start_date: str,
    end_date: str,
    session: int | None,
) -> pd.DataFrame:

    if not table_exists(
        connection,
        "market_price_data",
    ):

        raise RuntimeError(
            "market_price_data table "
            "does not exist."
        )

    country_placeholders = (
        ",".join(
            "?"
            for _ in countries
        )
    )

    query = f"""
        SELECT

            timestamp_utc,
            timestamp_market,
            market_date,
            period,

            country,

            market,
            market_stage,
            direction,
            session,

            price_value AS value,
            price_unit AS unit,

            native_resolution_minutes,

            source,
            source_id

        FROM market_price_data

        WHERE market = ?

          AND country IN (
              {country_placeholders}
          )

          AND market_date >= ?
          AND market_date <= ?
    """

    params = [
        market,
        *countries,
        start_date,
        end_date,
    ]

    if session is not None:

        query += """
            AND session = ?
        """

        params.append(
            session
        )

    query += """
        ORDER BY
            timestamp_utc,
            country,
            session,
            source_id;
    """

    frame = pd.read_sql_query(
        query,
        connection,
        params=params,
    )

    if frame.empty:

        return frame

    frame[
        "service"
    ] = None

    frame[
        "metric"
    ] = "price"

    return frame


# ==================================================
# BALANCING PRICE QUERY
#
# ESIOS + REN:
#
# afrr
# mfrr
# rr
# ==================================================

def load_balancing_prices(
    connection,
    service: str,
    countries: list[str],
    start_date: str,
    end_date: str,
    direction: str | None,
    market_stage: str | None,
    metric: str | None,
    source_id: str | None,
) -> pd.DataFrame:

    if not table_exists(
        connection,
        "balancing_market_data",
    ):

        raise RuntimeError(
            "balancing_market_data table "
            "does not exist."
        )

    country_placeholders = (
        ",".join(
            "?"
            for _ in countries
        )
    )

    query = f"""
        SELECT

            timestamp_utc,
            timestamp_market,
            market_date,
            period,

            country,

            service AS market,
            service,
            market_stage,
            metric,
            direction,

            NULL AS session,

            value,
            unit,

            resolution_minutes
                AS native_resolution_minutes,

            source,
            source_id

        FROM balancing_market_data

        WHERE service = ?

          AND country IN (
              {country_placeholders}
          )

          AND market_date >= ?
          AND market_date <= ?
    """

    params = [
        service,
        *countries,
        start_date,
        end_date,
    ]

    # ==================================================
    # DIRECTION
    # ==================================================

    if direction is not None:

        direction_value = (
            direction
            .strip()
            .lower()
        )

        if direction_value == "both":

            query += """
                AND direction IN (
                    'up',
                    'down'
                )
            """

        elif direction_value in {
            "up",
            "down",
            "none",
        }:

            query += """
                AND direction = ?
            """

            params.append(
                direction_value
            )

        elif direction_value not in {
            "all",
            "*",
        }:

            raise ValueError(
                "direction must be "
                "up, down, both, none "
                "or all."
            )

    # ==================================================
    # STAGE
    # ==================================================

    if market_stage is not None:

        query += """
            AND market_stage = ?
        """

        params.append(
            market_stage
        )

    # ==================================================
    # METRIC
    # ==================================================

    if metric is not None:

        query += """
            AND metric = ?
        """

        params.append(
            metric
        )

    # ==================================================
    # SOURCE SERIES
    # ==================================================

    if source_id is not None:

        query += """
            AND source_id = ?
        """

        params.append(
            source_id
        )

    query += """
        ORDER BY
            timestamp_utc,
            country,
            market_stage,
            metric,
            direction,
            source_id;
    """

    return pd.read_sql_query(
        query,
        connection,
        params=params,
    )


# ==================================================
# SERIES IDENTIFIER
#
# Critical rule:
#
# Never silently average economically different
# price series.
#
# Day-ahead / continuous:
# one series per country.
#
# Intraday auction:
# source_id must remain part of the identity,
# because overlapping auction instances can price
# the same delivery timestamp.
#
# Balancing:
# stage + metric + direction + source indicator
# remain separate.
# ==================================================

def build_series_id(
    row: pd.Series,
) -> str:

    market = row[
        "market"
    ]

    country = row[
        "country"
    ]

    if market in {
        "day_ahead",
        "intraday_continuous",
    }:

        return (
            f"{country}|"
            f"{market}"
        )

    if market == "intraday_auction":

        return (
            f"{country}|"
            f"intraday_auction|"
            f"session={int(row['session'])}|"
            f"{row['source_id']}"
        )

    return (
        f"{country}|"
        f"{market}|"
        f"{row['market_stage']}|"
        f"{row['metric']}|"
        f"{row['direction']}|"
        f"{row['source_id']}"
    )


# ==================================================
# PREPARE RAW DATA
# ==================================================

def prepare_raw_frame(
    frame: pd.DataFrame,
) -> pd.DataFrame:

    if frame.empty:

        return frame

    frame = frame.copy()

    frame[
        "timestamp_utc"
    ] = pd.to_datetime(
        frame[
            "timestamp_utc"
        ],
        utc=True,
    )

    frame[
        "native_resolution_minutes"
    ] = (
        frame[
            "native_resolution_minutes"
        ]
        .astype(int)
    )

    frame[
        "value"
    ] = (
        frame[
            "value"
        ]
        .astype(float)
    )

    frame[
        "series_id"
    ] = frame.apply(
        build_series_id,
        axis=1,
    )

    # ==================================================
    # DUPLICATE PROTECTION
    #
    # After series identity is defined, a single
    # series must not have two prices for exactly
    # the same UTC timestamp.
    # ==================================================

    duplicate_mask = (
        frame.duplicated(
            subset=[
                "series_id",
                "timestamp_utc",
            ],
            keep=False,
        )
    )

    if duplicate_mask.any():

        examples = (
            frame.loc[
                duplicate_mask,
                [
                    "series_id",
                    "timestamp_utc",
                    "value",
                ],
            ]
            .head(10)
            .to_dict(
                orient="records"
            )
        )

        raise ValueError(
            "Duplicate timestamps found "
            "inside a unified price series. "
            f"Examples: {examples}"
        )

    return frame


# ==================================================
# METADATA COLUMNS
# ==================================================

def metadata_from_group(
    group: pd.DataFrame,
) -> dict:

    first = group.iloc[
        0
    ]

    native_resolutions = sorted(
        {
            int(value)
            for value
            in group[
                "native_resolution_minutes"
            ]
        }
    )

    return {

        "series_id":
            first[
                "series_id"
            ],

        "country":
            first[
                "country"
            ],

        "market":
            first[
                "market"
            ],

        "market_stage":
            first[
                "market_stage"
            ],

        "metric":
            first[
                "metric"
            ],

        "direction":
            first[
                "direction"
            ],

        "session":
            (
                None
                if pd.isna(
                    first[
                        "session"
                    ]
                )
                else int(
                    first[
                        "session"
                    ]
                )
            ),

        "unit":
            first[
                "unit"
            ],

        "source":
            first[
                "source"
            ],

        "source_id":
            first[
                "source_id"
            ],

        "native_resolutions_minutes":
            native_resolutions,
    }


# ==================================================
# TIME-WEIGHTED MEAN
#
# If one part of a range is hourly and another
# is 15-minute, a simple row average would give
# quarter-hour observations four times the weight.
#
# Weight by each observation's native duration.
# ==================================================

def weighted_price_mean(
    group: pd.DataFrame,
) -> float:

    weights = (
        group[
            "native_resolution_minutes"
        ]
        .astype(float)
    )

    values = (
        group[
            "value"
        ]
        .astype(float)
    )

    denominator = (
        weights.sum()
    )

    if denominator == 0:

        return float(
            values.mean()
        )

    return float(
        (
            values
            * weights
        ).sum()
        / denominator
    )


# ==================================================
# DISPLAY = 15 MINUTES
#
# Native 15-minute:
# keep it.
#
# Native hourly:
# repeat the price at:
#
# HH:00
# HH:15
# HH:30
# HH:45
#
# Raw source remains unchanged in SQLite.
# ==================================================

def to_15_minute(
    frame: pd.DataFrame,
) -> pd.DataFrame:

    output_rows = []

    for _, row in frame.iterrows():

        native = int(
            row[
                "native_resolution_minutes"
            ]
        )

        if native < 15:

            raise ValueError(
                "Native resolution is finer "
                "than 15 minutes and is not "
                "currently supported."
            )

        if native % 15 != 0:

            raise ValueError(
                f"Cannot display native "
                f"{native}-minute data "
                f"at 15-minute resolution."
            )

        repeats = (
            native // 15
        )

        for step in range(
            repeats
        ):

            timestamp_utc = (
                row[
                    "timestamp_utc"
                ]
                + pd.Timedelta(
                    minutes=(
                        step
                        * 15
                    )
                )
            )

            timestamp_market = (
                timestamp_utc
                .tz_convert(
                    "Europe/Madrid"
                )
            )

            output_rows.append(
                {
                    "timestamp_utc":
                        timestamp_utc,

                    "timestamp_market":
                        timestamp_market,

                    "series_id":
                        row[
                            "series_id"
                        ],

                    "country":
                        row[
                            "country"
                        ],

                    "market":
                        row[
                            "market"
                        ],

                    "market_stage":
                        row[
                            "market_stage"
                        ],

                    "metric":
                        row[
                            "metric"
                        ],

                    "direction":
                        row[
                            "direction"
                        ],

                    "session":
                        (
                            None
                            if pd.isna(
                                row[
                                    "session"
                                ]
                            )
                            else int(
                                row[
                                    "session"
                                ]
                            )
                        ),

                    "value":
                        float(
                            row[
                                "value"
                            ]
                        ),

                    "unit":
                        row[
                            "unit"
                        ],

                    "source":
                        row[
                            "source"
                        ],

                    "source_id":
                        row[
                            "source_id"
                        ],

                    "native_resolution_minutes":
                        native,

                    "native_resolutions_minutes":
                        [
                            native
                        ],

                    "display_resolution":
                        "15min",

                    "display_resolution_minutes":
                        15,

                    "is_upsampled":
                        (
                            native > 15
                        ),

                    "aggregation":
                        (
                            "repeat"
                            if native > 15
                            else "none"
                        ),
                }
            )

    return pd.DataFrame(
        output_rows
    )


# ==================================================
# DISPLAY = 1 HOUR
# ==================================================

def to_hourly(
    frame: pd.DataFrame,
) -> pd.DataFrame:

    working = frame.copy()

    working[
        "bucket_utc"
    ] = (
        working[
            "timestamp_utc"
        ]
        .dt.floor(
            "h"
        )
    )

    output_rows = []

    for (
        series_id,
        bucket_utc,
    ), group in working.groupby(
        [
            "series_id",
            "bucket_utc",
        ],
        sort=True,
    ):

        metadata = metadata_from_group(
            group
        )

        native_resolutions = metadata[
            "native_resolutions_minutes"
        ]

        timestamp_market = (
            bucket_utc
            .tz_convert(
                "Europe/Madrid"
            )
        )

        output_rows.append(
            {
                "timestamp_utc":
                    bucket_utc,

                "timestamp_market":
                    timestamp_market,

                **metadata,

                "value":
                    weighted_price_mean(
                        group
                    ),

                "native_resolution_minutes":
                    (
                        native_resolutions[0]
                        if len(
                            native_resolutions
                        ) == 1
                        else None
                    ),

                "display_resolution":
                    "1h",

                "display_resolution_minutes":
                    60,

                "is_upsampled":
                    False,

                "aggregation":
                    (
                        "none"
                        if (
                            len(group) == 1
                            and native_resolutions
                            == [60]
                        )
                        else
                        "time_weighted_mean"
                    ),
            }
        )

    return pd.DataFrame(
        output_rows
    )


# ==================================================
# CALENDAR BUCKET
# ==================================================

def calendar_bucket(
    timestamp_market: pd.Timestamp,
    frequency: str,
) -> str:

    if frequency == "daily":

        return timestamp_market.strftime(
            "%Y-%m-%d"
        )

    if frequency == "weekly":

        monday = (
            timestamp_market
            .normalize()
            - pd.Timedelta(
                days=(
                    timestamp_market.weekday()
                )
            )
        )

        return monday.strftime(
            "%Y-%m-%d"
        )

    if frequency == "monthly":

        return timestamp_market.strftime(
            "%Y-%m"
        )

    if frequency == "yearly":

        return timestamp_market.strftime(
            "%Y"
        )

    raise ValueError(
        f"Unsupported calendar "
        f"frequency: {frequency}"
    )


def bucket_timestamp(
    bucket: str,
    frequency: str,
) -> pd.Timestamp:

    if frequency in {
        "daily",
        "weekly",
    }:

        value = bucket

    elif frequency == "monthly":

        value = (
            f"{bucket}-01"
        )

    elif frequency == "yearly":

        value = (
            f"{bucket}-01-01"
        )

    else:

        raise ValueError(
            f"Unsupported frequency: "
            f"{frequency}"
        )

    return (
        pd.Timestamp(
            value
        )
        .tz_localize(
            "Europe/Madrid"
        )
    )


# ==================================================
# DAILY / WEEKLY / MONTHLY / YEARLY
# ==================================================

def to_calendar_frequency(
    frame: pd.DataFrame,
    frequency: str,
) -> pd.DataFrame:

    working = frame.copy()

    working[
        "timestamp_market_calculated"
    ] = (
        working[
            "timestamp_utc"
        ]
        .dt.tz_convert(
            "Europe/Madrid"
        )
    )

    working[
        "bucket"
    ] = working[
        "timestamp_market_calculated"
    ].apply(
        lambda value:
            calendar_bucket(
                value,
                frequency,
            )
    )

    output_rows = []

    for (
        series_id,
        bucket,
    ), group in working.groupby(
        [
            "series_id",
            "bucket",
        ],
        sort=True,
    ):

        metadata = metadata_from_group(
            group
        )

        native_resolutions = metadata[
            "native_resolutions_minutes"
        ]

        timestamp_market = (
            bucket_timestamp(
                bucket,
                frequency,
            )
        )

        timestamp_utc = (
            timestamp_market
            .tz_convert(
                "UTC"
            )
        )

        output_rows.append(
            {
                "timestamp_utc":
                    timestamp_utc,

                "timestamp_market":
                    timestamp_market,

                **metadata,

                "value":
                    weighted_price_mean(
                        group
                    ),

                "native_resolution_minutes":
                    (
                        native_resolutions[0]
                        if len(
                            native_resolutions
                        ) == 1
                        else None
                    ),

                "display_resolution":
                    frequency,

                "display_resolution_minutes":
                    None,

                "is_upsampled":
                    False,

                "aggregation":
                    "time_weighted_mean",
            }
        )

    return pd.DataFrame(
        output_rows
    )


# ==================================================
# RESAMPLE
# ==================================================

def resample_prices(
    frame: pd.DataFrame,
    frequency: str,
) -> pd.DataFrame:

    if frame.empty:

        return frame

    if frequency == "15min":

        return to_15_minute(
            frame
        )

    if frequency == "1h":

        return to_hourly(
            frame
        )

    return to_calendar_frequency(
        frame,
        frequency,
    )


# ==================================================
# MARKET EVENTS
# ==================================================

def load_market_events(
    connection,
    market: str,
    countries: list[str],
    start_date: str,
    end_date: str,
) -> list[dict]:

    rows = []

    if table_exists(connection, "market_events"):
        placeholders = ",".join("?" for _ in countries)
        rows = connection.execute(
            f"""
        SELECT

            event_date,
            country,
            service,
            event_type,
            title,
            description,
            source

        FROM market_events

        WHERE service = ?

          AND country IN (
              {placeholders}
          )

          AND event_date >= ?
          AND event_date <= ?

        ORDER BY
            event_date,
            country,
            title;
            """,
            (market, *countries, start_date, end_date),
        ).fetchall()

    loaded = [
        {
            "event_date":
                readable_date(
                    row[0]
                ),

            "country":
                row[1],

            "service":
                row[2],

            "event_type":
                row[3],

            "title":
                row[4],

            "description":
                row[5],

            "source":
                row[6],
        }

        for row in rows
    ]

    # Keep database events authoritative, while supplying dated balancing
    # events to older deployments that predate the expanded event catalogue.
    known = {
        (
            item["event_date"],
            item["country"],
            item["service"],
            item["title"],
        )
        for item in loaded
    }

    for item in BUILTIN_MARKET_EVENTS:
        if (
            item["service"] != market
            or item["country"] not in countries
            or item["event_date"] < start_date
            or item["event_date"] > end_date
        ):
            continue

        key = (
            item["event_date"],
            item["country"],
            item["service"],
            item["title"],
        )
        if key not in known:
            loaded.append(
                {
                    **item,
                    "event_date": readable_date(item["event_date"]),
                }
            )
            known.add(key)

    return sorted(
        loaded,
        key=lambda item: (
            item["event_date"],
            item["country"],
            item["title"],
        ),
    )


# ==================================================
# JSON-SAFE DATA
# ==================================================

def dataframe_to_records(
    frame: pd.DataFrame,
) -> list[dict]:

    if frame.empty:

        return []

    frame = frame.copy()

    frame = frame.sort_values(
        [
            "timestamp_utc",
            "series_id",
        ]
    )

    records = []

    for _, row in frame.iterrows():

        native_value = row.get(
            "native_resolution_minutes"
        )

        if (
            native_value is None
            or pd.isna(
                native_value
            )
        ):

            native_value = None

        else:

            native_value = int(
                native_value
            )

        records.append(
            {
                "timestamp_utc":
                    row[
                        "timestamp_utc"
                    ].isoformat(),

                "timestamp_market":
                    row[
                        "timestamp_market"
                    ].isoformat(),

                "series_id":
                    row[
                        "series_id"
                    ],

                "country":
                    row[
                        "country"
                    ],

                "market":
                    row[
                        "market"
                    ],

                "market_stage":
                    row[
                        "market_stage"
                    ],

                "metric":
                    row[
                        "metric"
                    ],

                "direction":
                    row[
                        "direction"
                    ],

                "session":
                    row[
                        "session"
                    ],

                "value":
                    round(
                        float(
                            row[
                                "value"
                            ]
                        ),
                        6,
                    ),

                "unit":
                    row[
                        "unit"
                    ],

                "source":
                    row[
                        "source"
                    ],

                "source_id":
                    row[
                        "source_id"
                    ],

                "native_resolution_minutes":
                    native_value,

                "native_resolutions_minutes":
                    row[
                        "native_resolutions_minutes"
                    ],

                "display_resolution":
                    row[
                        "display_resolution"
                    ],

                "display_resolution_minutes":
                    row[
                        "display_resolution_minutes"
                    ],

                "is_upsampled":
                    bool(
                        row[
                            "is_upsampled"
                        ]
                    ),

                "aggregation":
                    row[
                        "aggregation"
                    ],
            }
        )

    return records


# ==================================================
# MAIN UNIFIED QUERY
# ==================================================

def get_unified_prices(
    market: str,
    country: str | list[str],
    start_date: str,
    end_date: str,
    frequency: str = "1h",
    direction: str | None = None,
    session: int | None = None,
    market_stage: str | None = None,
    metric: str | None = None,
    source_id: str | None = None,
) -> dict:

    market = (
        market
        .strip()
        .lower()
    )

    if market not in ALL_MARKETS:

        raise ValueError(
            f"Unsupported market: "
            f"{market}. "
            f"Allowed: "
            f"{sorted(ALL_MARKETS)}"
        )

    countries = (
        normalize_countries(
            country
        )
    )

    start_compact = (
        normalize_date(
            start_date
        )
    )

    end_compact = (
        normalize_date(
            end_date
        )
    )

    if (
        start_compact
        > end_compact
    ):

        raise ValueError(
            "start_date must be "
            "before end_date."
        )

    frequency = (
        normalize_frequency(
            frequency
        )
    )

    # ==================================================
    # SESSION VALIDATION
    # ==================================================

    if (
        session is not None
        and market
        != "intraday_auction"
    ):

        raise ValueError(
            "session can only be used "
            "with intraday_auction."
        )

    with get_database_connection() as connection:

        if market in WHOLESALE_MARKETS:

            raw = load_wholesale_prices(
                connection=
                    connection,

                market=
                    market,

                countries=
                    countries,

                start_date=
                    start_compact,

                end_date=
                    end_compact,

                session=
                    session,
            )

        else:

            raw = load_balancing_prices(
                connection=
                    connection,

                service=
                    market,

                countries=
                    countries,

                start_date=
                    start_compact,

                end_date=
                    end_compact,

                direction=
                    direction,

                market_stage=
                    market_stage,

                metric=
                    metric,

                source_id=
                    source_id,
            )

        events = load_market_events(
            connection=
                connection,

            market=
                market,

            countries=
                countries,

            start_date=
                start_compact,

            end_date=
                end_compact,
        )

    if raw.empty:

        return {

            "metadata": {
                "market":
                    market,

                "countries":
                    countries,

                "start_date":
                    readable_date(
                        start_compact
                    ),

                "end_date":
                    readable_date(
                        end_compact
                    ),

                "frequency":
                    frequency,

                "rows":
                    0,

                "series":
                    0,

                "upsampled_points":
                    0,

                "message":
                    (
                        "No official data "
                        "available for the "
                        "requested selection."
                    ),
            },

            "events":
                events,

            "data":
                [],
        }

    raw = prepare_raw_frame(
        raw
    )

    output = resample_prices(
        raw,
        frequency,
    )

    records = dataframe_to_records(
        output
    )

    series_count = len(
        {
            row[
                "series_id"
            ]
            for row in records
        }
    )

    upsampled_points = sum(
        1
        for row in records
        if row[
            "is_upsampled"
        ]
    )

    return {

        "metadata": {

            "market":
                market,

            "countries":
                countries,

            "start_date":
                readable_date(
                    start_compact
                ),

            "end_date":
                readable_date(
                    end_compact
                ),

            "frequency":
                frequency,

            "display_resolution_minutes":
                DISPLAY_MINUTES[
                    frequency
                ],

            "raw_rows":
                len(
                    raw
                ),

            "rows":
                len(
                    records
                ),

            "series":
                series_count,

            "upsampled_points":
                upsampled_points,

            "aggregation": (
                "repeat hourly values "
                "when displaying at 15min; "
                "time-weighted mean for "
                "coarser frequencies"
            ),
        },

        "events":
            events,

        "data":
            records,
    }


# ==================================================
# PRICE CATALOG
#
# This will feed the dashboard selectors later.
# ==================================================

def get_price_catalog() -> dict:

    wholesale = []

    balancing = []

    with get_database_connection() as connection:

        # ==================================================
        # WHOLESALE
        # ==================================================

        if table_exists(
            connection,
            "market_price_data",
        ):

            rows = connection.execute(
                """
                SELECT

                    country,
                    market,
                    market_stage,
                    direction,
                    session,
                    price_unit,

                    MIN(market_date),
                    MAX(market_date),

                    GROUP_CONCAT(
                        DISTINCT
                        native_resolution_minutes
                    )

                FROM market_price_data

                GROUP BY

                    country,
                    market,
                    market_stage,
                    direction,
                    session,
                    price_unit

                ORDER BY

                    market,
                    country,
                    session;
                """
            ).fetchall()

            for row in rows:

                wholesale.append(
                    {
                        "country":
                            row[0],

                        "market":
                            row[1],

                        "market_stage":
                            row[2],

                        "direction":
                            row[3],

                        "session":
                            row[4],

                        "unit":
                            row[5],

                        "first_date":
                            readable_date(
                                row[6]
                            ),

                        "last_date":
                            readable_date(
                                row[7]
                            ),

                        "native_resolutions_minutes":
                            sorted(
                                int(value)

                                for value
                                in row[8].split(
                                    ","
                                )
                            ),
                    }
                )

        # ==================================================
        # BALANCING
        # ==================================================

        if table_exists(
            connection,
            "balancing_market_data",
        ):

            rows = connection.execute(
                """
                SELECT

                    country,
                    service,
                    market_stage,
                    metric,
                    direction,
                    unit,
                    source,
                    source_id,

                    MIN(market_date),
                    MAX(market_date),

                    GROUP_CONCAT(
                        DISTINCT
                        resolution_minutes
                    )

                FROM balancing_market_data

                GROUP BY

                    country,
                    service,
                    market_stage,
                    metric,
                    direction,
                    unit,
                    source,
                    source_id

                ORDER BY

                    service,
                    country,
                    market_stage,
                    metric,
                    direction,
                    source_id;
                """
            ).fetchall()

            for row in rows:

                balancing.append(
                    {
                        "country":
                            row[0],

                        "market":
                            row[1],

                        "market_stage":
                            row[2],

                        "metric":
                            row[3],

                        "direction":
                            row[4],

                        "unit":
                            row[5],

                        "source":
                            row[6],

                        "source_id":
                            row[7],

                        "first_date":
                            readable_date(
                                row[8]
                            ),

                        "last_date":
                            readable_date(
                                row[9]
                            ),

                        "native_resolutions_minutes":
                            sorted(
                                int(value)

                                for value
                                in row[10].split(
                                    ","
                                )
                            ),
                    }
                )

    return {
        "wholesale":
            wholesale,

        "balancing":
            balancing,
    }


# ==================================================
# CLI
# ==================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Query the unified Iberian "
            "electricity price layer."
        )
    )

    parser.add_argument(
        "--catalog",
        action="store_true",
        help=(
            "Print available price "
            "series and exit."
        ),
    )

    parser.add_argument(
        "--market",
        help=(
            "day_ahead, "
            "intraday_auction, "
            "intraday_continuous, "
            "afrr, mfrr or rr"
        ),
    )

    parser.add_argument(
        "--country",
        default="both",
        help=(
            "ES, PT or both"
        ),
    )

    parser.add_argument(
        "--start",
        default="20260801",
    )

    parser.add_argument(
        "--end",
        default="20260803",
    )

    parser.add_argument(
        "--frequency",
        default="1h",
    )

    parser.add_argument(
        "--direction",
        default=None,
    )

    parser.add_argument(
        "--session",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--stage",
        default=None,
    )

    parser.add_argument(
        "--metric",
        default=None,
    )

    parser.add_argument(
        "--source-id",
        default=None,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
    )

    args = parser.parse_args()

    if args.catalog:

        catalog = (
            get_price_catalog()
        )

        print(
            json.dumps(
                catalog,
                indent=2,
                ensure_ascii=False,
            )
        )

        return

    if args.market is None:

        raise ValueError(
            "--market is required "
            "unless --catalog is used."
        )

    result = get_unified_prices(

        market=
            args.market,

        country=
            args.country,

        start_date=
            args.start,

        end_date=
            args.end,

        frequency=
            args.frequency,

        direction=
            args.direction,

        session=
            args.session,

        market_stage=
            args.stage,

        metric=
            args.metric,

        source_id=
            args.source_id,
    )

    print("=" * 90)
    print(
        "UNIFIED PRICE QUERY"
    )
    print("=" * 90)

    print(
        json.dumps(
            result[
                "metadata"
            ],
            indent=2,
            ensure_ascii=False,
        )
    )

    if result[
        "events"
    ]:

        print()
        print(
            "MARKET EVENTS"
        )

        print(
            json.dumps(
                result[
                    "events"
                ],
                indent=2,
                ensure_ascii=False,
            )
        )

    print()
    print(
        f"FIRST "
        f"{args.limit} DATA POINTS"
    )

    print(
        json.dumps(
            result[
                "data"
            ][
                :args.limit
            ],
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print("=" * 90)


if __name__ == "__main__":

    main()
