from __future__ import annotations

import json
import sqlite3

from functools import lru_cache
from typing import Literal

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from src.analytics.unified_prices import (
    get_unified_prices,
)

from src.config import (
    DATABASE_PATH,
    IS_PUBLIC,
)


router = APIRouter(
    prefix="/market",
    tags=["Market prices"],
)


# ============================================================
# PUBLIC / LOCAL MARKET ACCESS
# ============================================================

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

PUBLIC_BALANCING_MARKETS = {"afrr", "mfrr"}
PUBLIC_MARKETS = WHOLESALE_MARKETS | PUBLIC_BALANCING_MARKETS


def validate_public_market_access(
    market: str,
) -> None:
    """
    Public mode exposes OMIE wholesale data and validated Spanish
    REE/ESIOS aFRR and mFRR price series.

    Local development can use the complete research database,
    including ESIOS and REN balancing-market data.
    """

    if (
        IS_PUBLIC
        and market not in PUBLIC_MARKETS
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "This market is not available "
                "in the public demo."
            ),
        )


# ============================================================
# MATERIALISED MARKET CATALOG
# ============================================================

@lru_cache(maxsize=1)
def load_cached_market_catalog() -> dict:
    """
    Read the pre-built market catalogue from SQLite.

    The expensive catalogue computation is performed separately
    during the data-build process. The API therefore does not scan
    the full market tables every time /market/catalog is requested.
    """

    if not DATABASE_PATH.exists():
        raise RuntimeError(
            (
                "Market database was not found: "
                f"{DATABASE_PATH}"
            )
        )

    database_uri = (
        DATABASE_PATH
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
                "been built for this database."
            )
        ) from exc

    finally:

        connection.close()


    if row is None:

        raise RuntimeError(
            "The market catalog cache is empty."
        )


    try:

        catalog = json.loads(
            row[0]
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


    # Defence in depth:
    #
    # The public database should already contain only approved
    # OMIE wholesale and REE/ESIOS balancing series. Filter the
    # cached catalog again as defence in depth.

    if IS_PUBLIC:

        wholesale = [
            row
            for row in catalog.get(
                "wholesale",
                [],
            )
            if row.get("market")
            in WHOLESALE_MARKETS
        ]

        balancing = [
            row for row in catalog.get("balancing", [])
            if row.get("market") in PUBLIC_BALANCING_MARKETS
            and row.get("country") == "ES"
            and row.get("source") == "ESIOS"
        ]

        return {"wholesale": wholesale, "balancing": balancing}


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

    Local mode:
        wholesale + balancing markets

    Public mode:
        OMIE wholesale and validated Spanish REE/ESIOS aFRR/mFRR prices
    """

    validate_public_market_access(
        market
    )

    if IS_PUBLIC and market in PUBLIC_BALANCING_MARKETS and country != "ES":
        raise HTTPException(
            status_code=403,
            detail="Public ancillary-service prices are available for Spain only.",
        )

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

    Local mode:
        complete catalogue

    Public mode:
        approved OMIE and REE/ESIOS catalogue entries
    """

    try:

        return load_cached_market_catalog()

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
