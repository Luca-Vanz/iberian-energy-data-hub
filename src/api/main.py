from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import (
    FastAPI,
    HTTPException,
)

from fastapi.responses import FileResponse

from src.analytics.omie import (
    get_daily_market_summary,
    get_intraday_prices,
    get_prices,
)

from src.api.market_prices import (
    router as market_prices_router,
)

from src.config import (
    APP_MODE,
    DATABASE_PATH,
    IS_PUBLIC,
    WEB_PATH,
)


# ============================================================
# PATHS
# ============================================================

REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

WEB_FILE = (
    REPO_ROOT
    / WEB_PATH
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Iberian Energy Data Hub API",
    description=(
        "Historical electricity-market data "
        "for Spain and Portugal."
    ),
    version="0.4.0",
)


# ============================================================
# UNIFIED MARKET PRICE ROUTER
#
# Provides:
#
# /market/prices
# /market/catalog
# ============================================================

app.include_router(
    market_prices_router
)


# ============================================================
# DATE VALIDATION FOR LEGACY OMIE ENDPOINTS
# ============================================================

def validate_date(
    date: str | None,
) -> None:

    if date is None:
        return

    try:
        datetime.strptime(
            date,
            "%Y%m%d",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Date must be a valid "
                "calendar date in YYYYMMDD format."
            ),
        ) from exc


def validate_date_range(
    start_date: str | None,
    end_date: str | None,
) -> None:

    validate_date(
        start_date
    )

    validate_date(
        end_date
    )

    if (
        start_date is not None
        and end_date is not None
        and end_date < start_date
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "end_date cannot be "
                "before start_date."
            ),
        )


# ============================================================
# WEBSITE
#
# Local mode:
#   src/web/index.html
#
# Public mode:
#   src/web/public_index.html
# ============================================================

def serve_dashboard() -> FileResponse:

    if not WEB_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Dashboard HTML file "
                f"was not found: {WEB_FILE}"
            ),
        )

    return FileResponse(
        WEB_FILE
    )


@app.get(
    "/",
    include_in_schema=False,
)
def root():

    return serve_dashboard()


@app.get(
    "/dashboard",
    include_in_schema=False,
)
def dashboard():

    return serve_dashboard()


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/health",
    tags=["General"],
)
def health():

    return {
        "status": "ok",
        "mode": APP_MODE,
    }


# ============================================================
# ABOUT
# ============================================================

@app.get(
    "/about",
    tags=["General"],
)
def about():

    if IS_PUBLIC:

        markets = [
            "Day-ahead",
            "Intraday auctions",
            "Continuous intraday",
            "aFRR",
            "mFRR",
        ]

        sources = [
            "OMIE",
            "ESIOS",
        ]

    else:

        markets = [
            "Day-ahead",
            "Intraday auctions",
            "Continuous intraday",
            "aFRR",
            "mFRR",
            "RR",
        ]

        sources = [
            "OMIE",
            "ESIOS",
            "REN",
        ]

    return {
        "project":
            "Iberian Energy Data Hub",

        "description":
            (
                "A Python data-engineering and "
                "analytics project collecting, "
                "standardising and serving "
                "historical Iberian electricity-"
                "market data."
            ),

        "mode":
            APP_MODE,

        "public_demo":
            IS_PUBLIC,

        "database":
            DATABASE_PATH.name,

        "countries": [
            "Spain",
            "Portugal",
        ],

        "markets":
            markets,

        "sources":
            sources,

        "documentation":
            "/docs",

        "dashboard":
            "/dashboard",
    }


# ============================================================
# LEGACY OMIE DAILY SUMMARY
#
# Kept for backward compatibility with the existing public API.
# ============================================================

@app.get(
    "/omie/daily-summary",
    tags=["OMIE"],
)
def omie_daily_summary(
    start_date: str | None = None,
    end_date: str | None = None,
):

    validate_date_range(
        start_date,
        end_date,
    )

    try:

        frame = (
            get_daily_market_summary(
                start_date=start_date,
                end_date=end_date,
            )
        )

        return frame.to_dict(
            orient="records"
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not calculate "
                "OMIE daily summary: "
                f"{exc}"
            ),
        ) from exc


# ============================================================
# LEGACY OMIE PRICE OBSERVATIONS
#
# Kept so existing links/bookmarks/API users do not break.
# ============================================================

@app.get(
    "/omie/prices",
    tags=["OMIE"],
)
def omie_prices(
    zone: Literal[
        "ES",
        "PT",
    ],
    start_date: str | None = None,
    end_date: str | None = None,
):

    validate_date_range(
        start_date,
        end_date,
    )

    try:

        frame = get_prices(
            zone=zone,
            start_date=start_date,
            end_date=end_date,
        )

        return frame.to_dict(
            orient="records"
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not retrieve "
                "OMIE prices: "
                f"{exc}"
            ),
        ) from exc


# ============================================================
# LEGACY OMIE INTRADAY COMPARISON
#
# Despite the historical endpoint name, this is the existing
# ES/PT day-ahead period comparison used by the original app.
# It is preserved for compatibility.
# ============================================================

@app.get(
    "/omie/intraday",
    tags=["OMIE"],
)
def omie_intraday(
    date: str,
):

    validate_date(
        date
    )

    try:

        frame = (
            get_intraday_prices(
                date=date
            )
        )

        return frame.to_dict(
            orient="records"
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not retrieve "
                "OMIE intraday data: "
                f"{exc}"
            ),
        ) from exc


# ============================================================
# LOCAL-ONLY FUNDAMENTALS
#
# These routes are deliberately not registered in public mode.
# ============================================================

if not IS_PUBLIC:

    try:

        from src.analytics.price_load import (
            get_daily_price_load_summary,
            get_price_load,
        )


        @app.get(
            "/market/price-load",
            tags=["Local fundamentals"],
        )
        def market_price_load(
            country: Literal["PT"],
            date: str,
        ):

            validate_date(
                date
            )

            frame = get_price_load(
                country=country,
                date=date,
            )

            return frame.to_dict(
                orient="records"
            )


        @app.get(
            "/market/daily-price-load",
            tags=["Local fundamentals"],
        )
        def market_daily_price_load(
            start_date: str | None = None,
            end_date: str | None = None,
        ):

            validate_date_range(
                start_date,
                end_date,
            )

            frame = (
                get_daily_price_load_summary(
                    start_date=start_date,
                    end_date=end_date,
                )
            )

            return frame.to_dict(
                orient="records"
            )

    except ImportError:

        # Some development installations may not include
        # the optional fundamentals analytics module.
        # The main market API remains available.
        pass
