from __future__ import annotations

import sqlite3
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from src.config import DATABASE_PATH


router = APIRouter(prefix="/fundamentals", tags=["Fundamentals"])


def query(sql: str, parameters: tuple) -> list[dict]:
    if not DATABASE_PATH.exists():
        raise HTTPException(status_code=503, detail="Fundamentals database is unavailable.")
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        try:
            return [dict(row) for row in connection.execute(sql, parameters).fetchall()]
        except sqlite3.OperationalError as exc:
            raise HTTPException(status_code=503, detail="Fundamentals data is not installed.") from exc


def month_start(value: str | None, parameter: str) -> str | None:
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{parameter} must use YYYY-MM-DD.") from exc
    return parsed.replace(day=1).isoformat()


@router.get("/generation")
def generation(
    country: Literal["ES", "PT"],
    start_date: str | None = None,
    end_date: str | None = None,
    frequency: Literal["monthly", "yearly"] = "monthly",
):
    first = month_start(start_date, "start_date")
    last = month_start(end_date, "end_date")
    if first and last and first > last:
        raise HTTPException(status_code=422, detail="start_date must not be after end_date.")

    filters = ["country = ?"]
    parameters: list[str] = [country]
    if first:
        filters.append("month >= ?")
        parameters.append(first)
    if last:
        filters.append("month <= ?")
        parameters.append(last)
    where = " AND ".join(filters)

    if frequency == "yearly":
        sql = f"""SELECT substr(month, 1, 4) AS period, technology,
        ROUND(SUM(generation_mwh) / 1000.0, 3) AS generation_gwh,
        ROUND(SUM(observed_hours) / SUM(expected_hours), 4) AS coverage_ratio,
        source FROM entsoe_generation_monthly WHERE {where}
        GROUP BY period, technology, source ORDER BY period, technology"""
    else:
        sql = f"""SELECT month, month AS period, technology,
        ROUND(generation_mwh / 1000.0, 3) AS generation_gwh,
        ROUND(observed_hours / expected_hours, 4) AS coverage_ratio, source
        FROM entsoe_generation_monthly WHERE {where} ORDER BY period, technology"""
    return query(sql, tuple(parameters))


@router.get("/installed-capacity")
def installed_capacity(
    country: Literal["ES", "PT"],
    start_year: int | None = Query(default=None, ge=1900, le=2200),
    end_year: int | None = Query(default=None, ge=1900, le=2200),
):
    if start_year and end_year and start_year > end_year:
        raise HTTPException(status_code=422, detail="start_year must not be after end_year.")
    return query(
        """SELECT year, technology, capacity_mw, source
        FROM entsoe_installed_capacity WHERE country = ?
        AND (? IS NULL OR year >= ?) AND (? IS NULL OR year <= ?)
        ORDER BY year, technology""",
        (country, start_year, start_year, end_year, end_year),
    )
