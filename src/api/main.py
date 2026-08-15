from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from src.analytics.omie import (
    get_daily_market_summary,
    get_prices,
)


WEB_PATH = Path("src") / "web" / "index.html"


app = FastAPI(
    title="Iberian Energy Data Hub API",
    description="API for Iberian electricity market data and analytics.",
    version="0.1.0",
)


def validate_date(date: str | None) -> None:
    if date is None:
        return

    try:
        datetime.strptime(date, "%Y%m%d")
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Date must be a valid calendar date "
                "in YYYYMMDD format."
            ),
        ) from exc


@app.get("/")
def root():
    return FileResponse(WEB_PATH)


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.get("/omie/daily-summary")
def omie_daily_summary():
    df = get_daily_market_summary()

    return df.to_dict(
        orient="records"
    )


@app.get("/omie/prices")
def omie_prices(
    zone: Literal["ES", "PT"],
    start_date: str | None = None,
    end_date: str | None = None,
):
    validate_date(start_date)
    validate_date(end_date)

    if (
        start_date is not None
        and end_date is not None
        and end_date < start_date
    ):
        raise HTTPException(
            status_code=400,
            detail="end_date cannot be before start_date.",
        )

    df = get_prices(
        zone=zone,
        start_date=start_date,
        end_date=end_date,
    )

    return df.to_dict(
        orient="records"
    )