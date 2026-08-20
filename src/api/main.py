from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from src.analytics.omie import (
    get_daily_market_summary,
)

from src.api.market_prices import (
    router as market_prices_router,
)


# ==================================================
# PATHS
# ==================================================

WEB_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "web"
)

INDEX_FILE = (
    WEB_DIR
    / "index.html"
)


# ==================================================
# FASTAPI APPLICATION
# ==================================================

app = FastAPI(
    title="Iberian Energy Data Hub",
    description=(
        "Historical electricity-market data "
        "for Spain and Portugal."
    ),
    version="0.3.0",
)


# ==================================================
# UNIFIED MARKET PRICE ROUTER
#
# Adds:
#
# GET /market/prices
# GET /market/catalog
# ==================================================

app.include_router(
    market_prices_router
)


# ==================================================
# ROOT
# ==================================================

@app.get(
    "/",
    tags=["General"],
)
def root():

    return {
        "name":
            "Iberian Energy Data Hub",

        "status":
            "running",

        "dashboard":
            "/dashboard",

        "documentation":
            "/docs",

        "endpoints": {
            "health":
                "/health",

            "about":
                "/about",

            "omie_daily_summary":
                "/omie/daily-summary",

            "market_prices":
                "/market/prices",

            "market_catalog":
                "/market/catalog",
        },
    }


# ==================================================
# DASHBOARD
# ==================================================

@app.get(
    "/dashboard",
    include_in_schema=False,
)
def dashboard():

    if not INDEX_FILE.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Dashboard HTML file "
                "was not found."
            ),
        )

    return FileResponse(
        INDEX_FILE
    )


# ==================================================
# HEALTH
# ==================================================

@app.get(
    "/health",
    tags=["General"],
)
def health():

    return {
        "status":
            "ok"
    }


# ==================================================
# ABOUT
# ==================================================

@app.get(
    "/about",
    tags=["General"],
)
def about():

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

        "countries": [
            "Spain",
            "Portugal",
        ],

        "markets": [
            "Day-ahead",
            "Intraday auctions",
            "Continuous intraday",
            "aFRR",
            "mFRR",
            "RR",
        ],

        "sources": [
            "OMIE",
            "ESIOS",
            "REN",
        ],
    }


# ==================================================
# OMIE DAILY SUMMARY
# ==================================================

@app.get(
    "/omie/daily-summary",
    tags=["OMIE"],
)
def omie_daily_summary(
    date: str = Query(
        ...,
        description=(
            "Market date in YYYY-MM-DD "
            "or YYYYMMDD format."
        ),
    ),
):

    try:

        return get_daily_market_summary(
            date
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not calculate "
                "OMIE daily summary: "
                f"{exc}"
            ),
        ) from exc