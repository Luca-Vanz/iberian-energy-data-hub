from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from src.analytics.unified_prices import (
    get_price_catalog,
    get_unified_prices,
)


router = APIRouter(
    prefix="/market",
    tags=["Market prices"],
)


# ==================================================
# MARKET PRICES
# ==================================================

@router.get("/prices")
def market_prices(
    market: Literal[
        "day_ahead",
        "intraday_auction",
        "intraday_continuous",
        "afrr",
        "mfrr",
        "rr",
    ],

    country: Literal[
        "ES",
        "PT",
        "both",
    ] = "both",

    start_date: str = Query(
        ...,
        description=(
            "Start market date. "
            "YYYY-MM-DD or YYYYMMDD."
        ),
    ),

    end_date: str = Query(
        ...,
        description=(
            "End market date. "
            "YYYY-MM-DD or YYYYMMDD."
        ),
    ),

    frequency: Literal[
        "15min",
        "1h",
        "daily",
        "weekly",
        "monthly",
        "yearly",
    ] = "1h",

    direction: Literal[
        "up",
        "down",
        "both",
        "none",
        "all",
    ] | None = None,

    session: int | None = Query(
        default=None,
        ge=1,
        le=6,
        description=(
            "Intraday auction session. "
            "Only valid for "
            "intraday_auction."
        ),
    ),

    stage: str | None = Query(
        default=None,
        description=(
            "Balancing market stage, "
            "for example energy, "
            "capacity or "
            "energy_scheduled."
        ),
    ),

    metric: str | None = Query(
        default=None,
        description=(
            "Price metric, for example "
            "marginal_price or "
            "weighted_average_price."
        ),
    ),

    source_id: str | None = Query(
        default=None,
        description=(
            "Optional exact source "
            "series identifier."
        ),
    ),
):

    try:

        return get_unified_prices(
            market=market,
            country=country,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            direction=direction,
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


# ==================================================
# AVAILABLE SERIES
# ==================================================

@router.get("/catalog")
def market_catalog():

    try:

        return get_price_catalog()

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc