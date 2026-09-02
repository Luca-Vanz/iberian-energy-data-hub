import argparse
import io
import sqlite3
import zipfile
from pathlib import Path

import pandas as pd

from src.config import DATABASE_PATH, IS_PUBLIC


EXPECTED_SHEETS = {"Spain": "ES", "Portugal": "PT"}
EXPECTED_FIRST_DATE = {"ES": "19980101", "PT": "20070701"}
EXPECTED_LAST_DATE = "20250930"
SOURCE_ID = "marginalpdbc"


def create_market_price_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS market_price_data (
            timestamp_utc TEXT NOT NULL,
            timestamp_market TEXT NOT NULL,
            market_date TEXT NOT NULL,
            period INTEGER NOT NULL,
            country TEXT NOT NULL,
            market TEXT NOT NULL,
            market_stage TEXT NOT NULL,
            direction TEXT NOT NULL,
            session INTEGER NOT NULL,
            price_value REAL NOT NULL,
            price_unit TEXT NOT NULL,
            native_resolution_minutes INTEGER NOT NULL,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            PRIMARY KEY (
                timestamp_utc, country, market, market_stage,
                direction, session, source_id
            )
        )
        """
    )


def _find_workbook(archive: zipfile.ZipFile) -> str:
    workbooks = [
        name
        for name in archive.namelist()
        if name.lower().endswith(".xlsx") and not name.endswith("/")
    ]
    if len(workbooks) != 1:
        raise ValueError(
            "Expected exactly one XLSX workbook in the OMIE archive; "
            f"found {len(workbooks)}."
        )
    return workbooks[0]


def _build_country_rows(
    dataframe: pd.DataFrame,
    country: str,
) -> list[tuple]:
    if dataframe.shape[1] < 28:
        raise ValueError(
            f"Unexpected {country} worksheet width: "
            f"{dataframe.shape[1]} columns."
        )

    date_column = dataframe.columns[0]
    period_columns = list(dataframe.columns[1:26])
    mtu_column = dataframe.columns[-1]
    dates = pd.to_datetime(dataframe[date_column], errors="raise").dt.normalize()

    if dates.duplicated().any():
        raise ValueError(f"Duplicate market dates in {country} worksheet.")

    first_date = dates.min().strftime("%Y%m%d")
    last_date = dates.max().strftime("%Y%m%d")
    if first_date != EXPECTED_FIRST_DATE[country]:
        raise ValueError(f"Unexpected first {country} date: {first_date}.")
    if last_date != EXPECTED_LAST_DATE:
        raise ValueError(f"Unexpected last {country} date: {last_date}.")

    mtu_values = set(
        dataframe[mtu_column].dropna().astype(str).str.strip()
    )
    if mtu_values != {"MTU60"}:
        raise ValueError(
            f"Unexpected {country} MTU values: {sorted(mtu_values)}."
        )

    rows = []
    for row_index, market_date in dates.items():
        prices = pd.to_numeric(
            dataframe.loc[row_index, period_columns], errors="coerce"
        ).dropna().tolist()
        day_start = pd.Timestamp(market_date).tz_localize("Europe/Madrid")
        day_end = (
            pd.Timestamp(market_date) + pd.Timedelta(days=1)
        ).tz_localize("Europe/Madrid")
        timestamps = pd.date_range(
            start=day_start,
            end=day_end,
            freq="60min",
            inclusive="left",
        )

        if len(prices) != len(timestamps):
            date_text = market_date.strftime("%Y-%m-%d")
            raise ValueError(
                f"{country} {date_text} contains {len(prices)} prices; "
                f"{len(timestamps)} hourly periods are required by the "
                "Europe/Madrid calendar."
            )

        market_date_text = market_date.strftime("%Y%m%d")
        for period, (timestamp_market, price) in enumerate(
            zip(timestamps, prices), start=1
        ):
            rows.append(
                (
                    str(timestamp_market.tz_convert("UTC")),
                    str(timestamp_market),
                    market_date_text,
                    period,
                    country,
                    float(price),
                )
            )
    return rows


def read_historical_archive(archive_path: Path) -> list[tuple]:
    if not archive_path.exists():
        raise FileNotFoundError(
            f"OMIE historical archive not found: {archive_path}"
        )

    with zipfile.ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"Corrupt member in OMIE archive: {bad_member}")
        workbook_name = _find_workbook(archive)
        workbook_bytes = archive.read(workbook_name)

    excel = pd.ExcelFile(io.BytesIO(workbook_bytes))
    if set(excel.sheet_names) != set(EXPECTED_SHEETS):
        raise ValueError(
            f"Unexpected OMIE workbook sheets: {excel.sheet_names}."
        )

    rows = []
    for sheet_name, country in EXPECTED_SHEETS.items():
        dataframe = pd.read_excel(
            io.BytesIO(workbook_bytes), sheet_name=sheet_name
        )
        rows.extend(_build_country_rows(dataframe, country))
    return rows


def load_rows(connection: sqlite3.Connection, rows: list[tuple]) -> None:
    create_market_price_table(connection)
    connection.executemany(
        """
        INSERT INTO omie_day_ahead_prices (
            timestamp_utc, timestamp_market, market_date, period,
            bidding_zone, price_eur_mwh
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(timestamp_utc, bidding_zone)
        DO UPDATE SET
            timestamp_market = excluded.timestamp_market,
            market_date = excluded.market_date,
            period = excluded.period,
            price_eur_mwh = excluded.price_eur_mwh
        """,
        rows,
    )

    unified_rows = [
        (
            timestamp_utc,
            timestamp_market,
            market_date,
            period,
            country,
            "day_ahead",
            "energy",
            "none",
            0,
            price,
            "EUR/MWh",
            60,
            "OMIE",
            SOURCE_ID,
        )
        for (
            timestamp_utc,
            timestamp_market,
            market_date,
            period,
            country,
            price,
        ) in rows
    ]
    connection.executemany(
        """
        INSERT INTO market_price_data (
            timestamp_utc, timestamp_market, market_date, period,
            country, market, market_stage, direction, session,
            price_value, price_unit, native_resolution_minutes,
            source, source_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (
            timestamp_utc, country, market, market_stage,
            direction, session, source_id
        )
        DO UPDATE SET
            timestamp_market = excluded.timestamp_market,
            market_date = excluded.market_date,
            period = excluded.period,
            price_value = excluded.price_value,
            price_unit = excluded.price_unit,
            native_resolution_minutes = excluded.native_resolution_minutes,
            source = excluded.source
        """,
        unified_rows,
    )


def report(connection: sqlite3.Connection) -> None:
    results = connection.execute(
        """
        SELECT country, MIN(market_date), MAX(market_date), COUNT(*)
        FROM market_price_data
        WHERE market = 'day_ahead' AND source = 'OMIE'
        GROUP BY country
        ORDER BY country
        """
    ).fetchall()
    print("OMIE historical day-ahead import complete")
    for country, first_date, last_date, count in results:
        print(f"  {country}: {first_date} to {last_date} ({count:,} rows)")


def main() -> None:
    if IS_PUBLIC:
        raise RuntimeError(
            "Historical imports must run in local mode, not public mode."
        )

    parser = argparse.ArgumentParser(
        description="Load the OMIE-supplied historical day-ahead workbook."
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--database",
        type=Path,
        default=DATABASE_PATH,
        help="SQLite database to update.",
    )
    args = parser.parse_args()

    rows = read_historical_archive(args.archive)
    args.database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.database) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS omie_day_ahead_prices (
                timestamp_utc TEXT NOT NULL,
                timestamp_market TEXT NOT NULL,
                market_date TEXT NOT NULL,
                period INTEGER NOT NULL,
                bidding_zone TEXT NOT NULL,
                price_eur_mwh REAL NOT NULL,
                PRIMARY KEY (timestamp_utc, bidding_zone)
            )
            """
        )
        load_rows(connection, rows)
        connection.commit()
        report(connection)


if __name__ == "__main__":
    main()
