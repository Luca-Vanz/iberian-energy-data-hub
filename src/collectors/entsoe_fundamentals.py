from __future__ import annotations

import argparse
import os
import sqlite3
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv


API_URL = "https://web-api.tp.entsoe.eu/api"
DATABASE_PATH = Path("data/database/iberian_energy.db")
RAW_DIR = Path("data/raw/entsoe/fundamentals")
AREAS = {
    "ES": "10YES-REE------0",
    "PT": "10YPT-REN------W",
}
PRODUCTION_TYPES = {
    "B01": "biomass", "B02": "lignite", "B03": "coal_gas",
    "B04": "natural_gas", "B05": "hard_coal", "B06": "oil",
    "B07": "oil_shale", "B08": "peat", "B09": "geothermal",
    "B10": "hydro_pumped_storage", "B11": "hydro_run_of_river",
    "B12": "hydro_reservoir", "B13": "marine", "B14": "nuclear",
    "B15": "other_renewable", "B16": "solar", "B17": "waste",
    "B18": "wind_offshore", "B19": "wind_onshore",
    "B20": "other", "B25": "energy_storage",
}
RESOLUTION_HOURS = {"PT15M": 0.25, "PT30M": 0.5, "PT60M": 1.0, "P1Y": 8760.0}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(node: ET.Element, name: str) -> str | None:
    for child in node.iter():
        if local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def create_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS entsoe_generation_monthly (
            month TEXT NOT NULL, country TEXT NOT NULL, technology TEXT NOT NULL,
            generation_mwh REAL NOT NULL, observed_hours REAL NOT NULL,
            expected_hours REAL NOT NULL, source TEXT NOT NULL,
            PRIMARY KEY (month, country, technology)
        );
        CREATE TABLE IF NOT EXISTS entsoe_installed_capacity (
            year INTEGER NOT NULL, country TEXT NOT NULL, technology TEXT NOT NULL,
            capacity_mw REAL NOT NULL, source TEXT NOT NULL,
            PRIMARY KEY (year, country, technology)
        );
        CREATE INDEX IF NOT EXISTS idx_entsoe_generation_country_month
            ON entsoe_generation_monthly(country, month);
        CREATE INDEX IF NOT EXISTS idx_entsoe_capacity_country_year
            ON entsoe_installed_capacity(country, year);
        """
    )


def request_xml(token: str, params: dict[str, str], raw_path: Path) -> bytes:
    if raw_path.exists():
        return raw_path.read_bytes()
    response = requests.get(
        API_URL,
        params={"securityToken": token, **params},
        timeout=90,
        headers={"User-Agent": "iberian-energy-data-hub/1.0"},
    )
    if not response.ok:
        detail = ""
        try:
            detail = child_text(ET.fromstring(response.content), "text") or ""
        except ET.ParseError:
            pass
        raise RuntimeError(
            f"ENTSO-E request failed with HTTP {response.status_code}"
            + (f": {detail}" if detail else "")
        )
    if b"Acknowledgement_MarketDocument" in response.content:
        reason = child_text(ET.fromstring(response.content), "text") or "ENTSO-E returned an acknowledgement"
        raise RuntimeError(reason)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(response.content)
    time.sleep(0.25)
    return response.content


def parse_generation(xml_bytes: bytes, country: str) -> list[tuple]:
    root = ET.fromstring(xml_bytes)
    totals: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for series in (node for node in root.iter() if local_name(node.tag) == "TimeSeries"):
        if child_text(series, "businessType") != "A01":
            continue
        # ENTSO-E uses an out-domain series for storage/pumping consumption.
        # This dataset is generation only, so retain in-domain output series.
        if child_text(series, "inBiddingZone_Domain.mRID") is None:
            continue
        psr = child_text(series, "psrType")
        technology = PRODUCTION_TYPES.get(psr or "")
        if not technology:
            continue
        curve_type = child_text(series, "curveType")
        periods = [n for n in series if local_name(n.tag) == "Period"]
        for period in periods:
            start_text = child_text(period, "start")
            end_text = child_text(period, "end")
            resolution = child_text(period, "resolution")
            hours = RESOLUTION_HOURS.get(resolution or "")
            if not start_text or not end_text or hours is None:
                raise ValueError(f"Unsupported ENTSO-E generation resolution: {resolution}")
            start = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_text.replace("Z", "+00:00"))
            total_positions = round((end - start).total_seconds() / 3600 / hours)
            points = []
            for point in (n for n in period if local_name(n.tag) == "Point"):
                position_text = child_text(point, "position")
                quantity_text = child_text(point, "quantity")
                if position_text and quantity_text is not None:
                    points.append((int(position_text), float(quantity_text)))
            points.sort()
            for index, (position, quantity) in enumerate(points):
                span = 1
                if curve_type == "A03":
                    next_position = points[index + 1][0] if index + 1 < len(points) else total_positions + 1
                    span = next_position - position
                if span < 1:
                    raise ValueError("Invalid ENTSO-E step-curve positions")
                for offset in range(span):
                    effective_position = position + offset
                    if effective_position > total_positions:
                        break
                    stamp = start + timedelta(hours=(effective_position - 1) * hours)
                    month = stamp.strftime("%Y-%m-01")
                    bucket = totals[(month, technology)]
                    bucket[0] += quantity * hours
                    bucket[1] += hours
    rows = []
    for (month, technology), (generation_mwh, observed_hours) in sorted(totals.items()):
        start = datetime.strptime(month, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        following = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        expected_hours = (following - start).total_seconds() / 3600
        rows.append((month, country, technology, generation_mwh, observed_hours, expected_hours, "ENTSO-E"))
    return rows


def parse_capacity(xml_bytes: bytes, country: str) -> list[tuple]:
    root = ET.fromstring(xml_bytes)
    rows = []
    for series in (node for node in root.iter() if local_name(node.tag) == "TimeSeries"):
        technology = PRODUCTION_TYPES.get(child_text(series, "psrType") or "")
        period = next((n for n in series.iter() if local_name(n.tag) == "Period"), None)
        if not technology or period is None:
            continue
        start_text = child_text(period, "start")
        quantity = child_text(period, "quantity")
        if start_text and quantity is not None:
            zone = ZoneInfo("Europe/Madrid" if country == "ES" else "Europe/Lisbon")
            year = datetime.fromisoformat(start_text.replace("Z", "+00:00")).astimezone(zone).year
            rows.append((year, country, technology, float(quantity), "ENTSO-E"))
    return rows


def collect(start_year: int, end_year: int) -> None:
    load_dotenv(".env")
    token = os.getenv("ENTSOE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("ENTSOE_API_TOKEN is not configured")
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        create_tables(connection)
        connection.execute(
            "DELETE FROM entsoe_installed_capacity WHERE year BETWEEN ? AND ?",
            (start_year, end_year + 1),
        )
        for country, area in AREAS.items():
            jobs = []
            for year in range(start_year, end_year + 1):
                for month in range(1, 13):
                    if year == datetime.now().year and month > datetime.now().month:
                        break
                    start_dt = datetime(year, month, 1)
                    end_dt = (
                        datetime(year + 1, 1, 1)
                        if month == 12
                        else datetime(year, month + 1, 1)
                    )
                    start = start_dt.strftime("%Y%m%d%H%M")
                    end = end_dt.strftime("%Y%m%d%H%M")
                    jobs.append((year, month, {
                        "documentType": "A75", "processType": "A16",
                        "in_Domain": area, "periodStart": start, "periodEnd": end,
                    }, RAW_DIR / country.lower() / f"generation_{year}_{month:02d}.xml"))
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(request_xml, token, params, path): (year, month)
                    for year, month, params, path in jobs
                }
                for future in as_completed(futures):
                    year, month = futures[future]
                    generation_rows = parse_generation(future.result(), country)
                    connection.executemany(
                        """INSERT INTO entsoe_generation_monthly VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(month, country, technology) DO UPDATE SET
                        generation_mwh=excluded.generation_mwh,
                        observed_hours=excluded.observed_hours,
                        expected_hours=excluded.expected_hours, source=excluded.source""",
                        generation_rows,
                    )
                    print(f"{country} {year}-{month:02d}: {len(generation_rows)} generation rows")
            for year in range(start_year, end_year + 1):
                capacity_xml = request_xml(token, {
                    "documentType": "A68", "processType": "A33", "in_Domain": area,
                    "periodStart": f"{year}01010000",
                    "periodEnd": f"{year + 1}01010000",
                }, RAW_DIR / country.lower() / f"capacity_{year}.xml")
                capacity_rows = parse_capacity(capacity_xml, country)
                connection.executemany(
                    """INSERT INTO entsoe_installed_capacity VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(year, country, technology) DO UPDATE SET
                    capacity_mw=excluded.capacity_mw, source=excluded.source""",
                    capacity_rows,
                )
                print(f"{country} {year}: {len(capacity_rows)} installed-capacity rows")
        connection.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect ENTSO-E generation and capacity fundamentals")
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=datetime.now().year)
    args = parser.parse_args()
    collect(args.start_year, args.end_year)
