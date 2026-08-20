from __future__ import annotations

import json
import os
import sqlite3

from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from src.analytics.unified_prices import (
    get_unified_prices,
)


router = APIRouter(
    prefix="/market",
    tags=["Market prices"],
)


# ============================================================
# DATABASE PATHS
# ============================================================

REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

LOCAL_DATABASE_PATH = (
    REPO_ROOT
    / "data"
    / "database"
    / "iberian_energy.db"
)

PUBLIC_DATABASE_PATH = (
    REPO_ROOT
    / "deployment"
    / "iberian_energy_public.db"
)


def get_database_path() -> Path:
    """
    Return the database used by the current application mode.

    Local development:
        data/database/iberian_energy.db

    Public deployment:
        deployment/iberian_energy_public.db
    """

    app_mode = (
        os.getenv(
            "IBERIAN_APP_MODE",
            "local",
        )
        .strip()
        .lower()
    )

    if app_mode == "public":
        return PUBLIC_DATABASE_PATH

    return LOCAL_DATABASE_PATH


# ============================================================
# FAST MATERIALISED MARKET CATALOG
# ============================================================

@lru_cache(maxsize=1)
def load_cached_market_catalog() -> dict:
    """
    Load the materialised market catalog.

    The expensive catalog computation is performed separately by:

        python -m src.database.build_market_catalog_cache

    The API therefore does not scan millions of market rows
    every time /market/catalog is requested.
    """

    database_path = (
        get_database_path()
    )

    if not database_path.exists():
        raise RuntimeError(
            (
                "Market database was not found: "
                f"{database_path}"
            )
        )

    database_uri = (
        database_path
        .resolve()
        .as_uri()
        + "?mode=ro"
    )

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    try:
        row = connection.execute(
            """
            SELECT
                payload_json,
                built_at_utc
            FROM market_catalog_cache
            WHERE id = 1
            """
        ).fetchone()

    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            (
                "The market catalog cache has not "
                "been built yet. Run: "
                "python -m "
                "src.database.build_market_catalog_cache"
            )
        ) from exc

    finally:
        connection.close()

    if row is None:
        raise RuntimeError(
            (
                "The market catalog cache is empty. "
                "Run: python -m "
                "src.database.build_market_catalog_cache"
            )
        )

    payload_json = row[0]

    try:
        catalog = json.loads(
            payload_json
        )

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            (
                "The cached market catalog "
                "contains invalid JSON."
            )
        ) from exc

    if not isinstance(
        catalog,
        dict,
    ):
        raise RuntimeError(
            (
                "The cached market catalog "
                "has an invalid structure."
            )
        )

    return catalog


# ============================================================
# UNIFIED MARKET PRICE ENDPOINT
# ============================================================

@router.get("/prices")
def market_prices(
    market: Literal[
        "day_ahead",
        "intraday_auction",
        "intraday_continuous",
        "afrr",
        "mfrr",
        "rr",
    ] = Query(...),

    country: Literal[
        "ES",
        "PT",
        "both",
    ] = Query(...),

    start_date: str = Query(...),

    end_date: str = Query(...),

    frequency: Literal[
        "15min",
        "1h",
        "daily",
        "weekly",
        "monthly",
        "yearly",
    ] = Query("1h"),

    direction: Literal[
        "up",
        "down",
        "both",
        "none",
        "all",
    ]
    | None = Query(None),

    session: int
    | None = Query(
        None,
        ge=1,
        le=6,
    ),

    stage: str
    | None = Query(None),

    metric: str
    | None = Query(None),

    source_id: str
    | None = Query(None),
):
    """
    Return a unified electricity-market price series.

    The analytics layer handles:

    - wholesale and balancing markets
    - ES / PT / both
    - native-resolution preservation
    - finer-resolution repetition
    - coarser time aggregation
    - market-event metadata
    """

    try:
        return get_unified_prices(
            market=market,
            country=country,
            direction=direction,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            session=session,
            market_stage=stage,
            metric=metric,
            source_id=source_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


# ============================================================
# MARKET CATALOG ENDPOINT
# ============================================================

@router.get("/catalog")
def market_catalog():
    """
    Return available market-price series.

    This endpoint reads a small materialised cache rather than
    recomputing availability from millions of price observations.
    """

    try:
        return load_cached_market_catalog()

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc