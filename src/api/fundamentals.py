from __future__ import annotations

import sqlite3
from typing import Literal

from fastapi import APIRouter, HTTPException

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


@router.get("/generation")
def generation(country: Literal["ES", "PT"]):
    return query(
        """SELECT month, technology, ROUND(generation_mwh / 1000.0, 3) AS generation_gwh,
        ROUND(observed_hours / expected_hours, 4) AS coverage_ratio, source
        FROM entsoe_generation_monthly WHERE country = ? ORDER BY month, technology""",
        (country,),
    )


@router.get("/installed-capacity")
def installed_capacity(country: Literal["ES", "PT"]):
    return query(
        """SELECT year, technology, capacity_mw, source
        FROM entsoe_installed_capacity WHERE country = ? ORDER BY year, technology""",
        (country,),
    )
