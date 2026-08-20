from __future__ import annotations

import sys
import time
from collections import Counter
from typing import Any

import requests


BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 30


# ============================================================
# TEST INFRASTRUCTURE
# ============================================================

passed = 0
failed = 0
warnings = 0


class SmokeTestFailure(AssertionError):
    pass


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeTestFailure(message)


def normalize_date(value: Any) -> str:
    text = str(value)

    if len(text) >= 10 and "-" in text[:10]:
        return text[:10]

    if len(text) >= 8 and text[:8].isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"

    return text


def request_json(
    path: str,
    params: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], float]:
    url = f"{BASE_URL}{path}"

    start = time.perf_counter()

    response = requests.get(
        url,
        params=params,
        timeout=TIMEOUT_SECONDS,
    )

    elapsed = time.perf_counter() - start

    assert_true(
        response.status_code == 200,
        (
            f"HTTP {response.status_code} from {response.url}\n"
            f"Response: {response.text[:1000]}"
        ),
    )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SmokeTestFailure(
            f"Response from {response.url} is not valid JSON."
        ) from exc

    return payload, elapsed


def data_rows(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = payload.get("data", [])

    assert_true(
        isinstance(rows, list),
        "API response field 'data' is not a list.",
    )

    return rows


def print_timing(elapsed: float) -> None:
    global warnings

    print(f"    API time: {elapsed:.3f} s")

    if elapsed > 2.0:
        warnings += 1
        print(
            "    WARNING: request took more than 2 seconds"
        )


def run_test(
    name: str,
    test_function,
) -> None:
    global passed, failed

    print()
    print("=" * 72)
    print(name)
    print("=" * 72)

    try:
        test_function()

    except Exception as exc:
        failed += 1
        print(f"FAIL: {exc}")

    else:
        passed += 1
        print("PASS")


# ============================================================
# 1. HEALTH
# ============================================================

def test_health() -> None:
    payload, elapsed = request_json(
        "/health"
    )

    print_timing(elapsed)

    assert_true(
        payload.get("status") == "ok",
        f"Unexpected health response: {payload}",
    )


# ============================================================
# 2. MARKET CATALOG
# ============================================================

def test_catalog() -> None:
    payload, elapsed = request_json(
        "/market/catalog"
    )

    print_timing(elapsed)

    wholesale = payload.get(
        "wholesale",
        [],
    )

    balancing = payload.get(
        "balancing",
        [],
    )

    assert_true(
        isinstance(wholesale, list)
        and len(wholesale) > 0,
        "Wholesale catalog is empty.",
    )

    assert_true(
        isinstance(balancing, list)
        and len(balancing) > 0,
        "Balancing catalog is empty.",
    )

    day_ahead = [
        row
        for row in wholesale
        if row.get("market") == "day_ahead"
    ]

    countries = {
        row.get("country")
        for row in day_ahead
    }

    assert_true(
        countries == {"ES", "PT"},
        (
            "Unexpected day-ahead countries: "
            f"{countries}"
        ),
    )

    print(
        f"    Wholesale catalog rows: "
        f"{len(wholesale)}"
    )

    print(
        f"    Balancing catalog rows: "
        f"{len(balancing)}"
    )

    print(
        f"    Day-ahead countries: "
        f"{sorted(countries)}"
    )


# ============================================================
# 3. DAY-AHEAD ES — ONE DAY — HOURLY
#
# 3 Aug 2026 is natively 15-minute.
# 96 QH observations must become 24 hourly points.
# ============================================================

def test_day_ahead_es_hourly() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "day_ahead",
            "country": "ES",
            "start_date": "2026-08-03",
            "end_date": "2026-08-03",
            "frequency": "1h",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) == 24,
        (
            "Expected 24 hourly points, "
            f"got {len(rows)}."
        ),
    )

    assert_true(
        {
            row.get("country")
            for row in rows
        } == {"ES"},
        (
            "Unexpected country in ES "
            "day-ahead response."
        ),
    )

    assert_true(
        all(
            row.get("unit") == "EUR/MWh"
            for row in rows
        ),
        "Unexpected unit in day-ahead response.",
    )

    assert_true(
        not any(
            bool(row.get("is_upsampled"))
            for row in rows
        ),
        (
            "Hourly aggregation should not "
            "be marked as upsampling."
        ),
    )

    print(
        f"    Display points: {len(rows)}"
    )


# ============================================================
# 4. DAY-AHEAD BOTH COUNTRIES — ONE DAY — HOURLY
# ============================================================

def test_day_ahead_both_hourly() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "day_ahead",
            "country": "both",
            "start_date": "2026-08-03",
            "end_date": "2026-08-03",
            "frequency": "1h",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) == 48,
        (
            "Expected 48 total points, "
            f"got {len(rows)}."
        ),
    )

    counts = Counter(
        row.get("country")
        for row in rows
    )

    assert_true(
        counts["ES"] == 24,
        (
            "Expected 24 ES points, "
            f"got {counts['ES']}."
        ),
    )

    assert_true(
        counts["PT"] == 24,
        (
            "Expected 24 PT points, "
            f"got {counts['PT']}."
        ),
    )

    print(
        f"    ES points: {counts['ES']}"
    )

    print(
        f"    PT points: {counts['PT']}"
    )


# ============================================================
# 5. DAY-AHEAD RESOLUTION TRANSITION
#
# 29 Sep – 2 Oct 2025:
#
# 29–30 Sep:
#   native hourly
#   repeated to 15 min
#   2 × 96 = 192 display points
#
# 1–2 Oct:
#   native 15 min
#   2 × 96 = 192 display points
#
# Total = 384
# Upsampled = 192
# ============================================================

def test_day_ahead_resolution_transition() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "day_ahead",
            "country": "ES",
            "start_date": "2025-09-29",
            "end_date": "2025-10-02",
            "frequency": "15min",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) == 384,
        (
            "Expected 384 display points, "
            f"got {len(rows)}."
        ),
    )

    upsampled = [
        row
        for row in rows
        if bool(
            row.get("is_upsampled")
        )
    ]

    assert_true(
        len(upsampled) == 192,
        (
            "Expected 192 repeated "
            "pre-transition observations, "
            f"got {len(upsampled)}."
        ),
    )

    events = payload.get(
        "events",
        [],
    )

    event_dates = {
        normalize_date(
            event.get("event_date")
        )
        for event in events
    }

    assert_true(
        "2025-10-01" in event_dates,
        (
            "Expected the 2025-10-01 "
            "day-ahead resolution-change event."
        ),
    )

    print(
        f"    Display points: {len(rows)}"
    )

    print(
        f"    Upsampled points: "
        f"{len(upsampled)}"
    )

    print(
        f"    Event dates: "
        f"{sorted(event_dates)}"
    )


# ============================================================
# 6. INTRADAY AUCTION — SESSION 1 — THREE COMPLETE DAYS
#
# 1–3 Aug 2026 were confirmed to contain full official files.
#
# 3 days × 96 periods = 288 observations.
# Each auction instance must retain its own source_id.
# ============================================================

def test_intraday_auction_session_1_complete_days() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "intraday_auction",
            "country": "ES",
            "start_date": "2026-08-01",
            "end_date": "2026-08-03",
            "frequency": "15min",
            "session": 1,
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) == 288,
        (
            "Expected 288 session-1 observations "
            "for 1–3 Aug 2026, "
            f"got {len(rows)}."
        ),
    )

    assert_true(
        all(
            int(
                row.get(
                    "session",
                    0,
                )
            ) == 1
            for row in rows
        ),
        (
            "Response contains an auction "
            "session other than session 1."
        ),
    )

    assert_true(
        all(
            row.get("country") == "ES"
            for row in rows
        ),
        (
            "Unexpected country in "
            "intraday-auction response."
        ),
    )

    source_ids = {
        row.get("source_id")
        for row in rows
        if row.get("source_id")
    }

    expected_source_ids = {
        "marginalpibc_2026080101",
        "marginalpibc_2026080201",
        "marginalpibc_2026080301",
    }

    assert_true(
        source_ids == expected_source_ids,
        (
            "Unexpected source IDs. "
            f"Expected {sorted(expected_source_ids)}, "
            f"got {sorted(source_ids)}."
        ),
    )

    rows_by_delivery_date = Counter(
        row["timestamp_market"][:10]
        for row in rows
    )

    expected_counts = {
        "2026-08-01": 96,
        "2026-08-02": 96,
        "2026-08-03": 96,
    }

    assert_true(
        dict(rows_by_delivery_date)
        == expected_counts,
        (
            "Unexpected intraday-auction "
            "daily row counts: "
            f"{dict(rows_by_delivery_date)}"
        ),
    )

    print(
        f"    Display points: {len(rows)}"
    )

    print(
        f"    Auction instances: "
        f"{len(source_ids)}"
    )

    print(
        f"    Daily counts: "
        f"{dict(rows_by_delivery_date)}"
    )


# ============================================================
# 7. INTRADAY AUCTION — KNOWN EMPTY OFFICIAL FILES
#
# 4 and 5 Aug 2026 session-1 files exist at OMIE but are only
# 18 bytes and contain no delivery prices.
#
# Correct behavior = no observations.
# ============================================================

def test_intraday_auction_known_empty_files() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "intraday_auction",
            "country": "ES",
            "start_date": "2026-08-04",
            "end_date": "2026-08-05",
            "frequency": "15min",
            "session": 1,
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) == 0,
        (
            "Known empty OMIE session-1 files "
            "should produce zero observations. "
            f"Got {len(rows)} rows."
        ),
    )

    print(
        "    Correctly preserved the official "
        "empty-file gap"
    )


# ============================================================
# 8. CONTINUOUS INTRADAY — BOTH COUNTRIES
# ============================================================

def test_intraday_continuous_both() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "intraday_continuous",
            "country": "both",
            "start_date": "2026-08-03",
            "end_date": "2026-08-03",
            "frequency": "15min",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) == 192,
        (
            "Expected 192 continuous-intraday "
            "points for ES + PT, "
            f"got {len(rows)}."
        ),
    )

    counts = Counter(
        row.get("country")
        for row in rows
    )

    assert_true(
        counts["ES"] == 96
        and counts["PT"] == 96,
        (
            "Unexpected country counts: "
            f"{dict(counts)}"
        ),
    )

    print(
        f"    Country counts: {dict(counts)}"
    )


# ============================================================
# 9. SPAIN aFRR ENERGY — NATIVE 15 MIN
# ============================================================

def test_es_afrr_energy() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "afrr",
            "country": "ES",
            "start_date": "2026-08-03",
            "end_date": "2026-08-03",
            "frequency": "15min",
            "direction": "both",
            "stage": "energy",
            "metric": "marginal_price",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) == 192,
        (
            "Expected 192 ES aFRR points, "
            f"got {len(rows)}."
        ),
    )

    directions = {
        row.get("direction")
        for row in rows
    }

    assert_true(
        directions == {
            "up",
            "down",
        },
        (
            "Unexpected directions: "
            f"{directions}"
        ),
    )

    assert_true(
        not any(
            bool(
                row.get("is_upsampled")
            )
            for row in rows
        ),
        (
            "Modern ES aFRR should be "
            "native 15-minute here."
        ),
    )

    print(
        f"    Directions: "
        f"{sorted(directions)}"
    )

    print(
        f"    Display points: {len(rows)}"
    )


# ============================================================
# 10. PORTUGAL aFRR ENERGY — HOURLY → 15 MIN DISPLAY
#
# 24 hours × 2 directions × 4 = 192
# ============================================================

def test_pt_afrr_hourly_to_quarter_hour() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "afrr",
            "country": "PT",
            "start_date": "2026-08-03",
            "end_date": "2026-08-03",
            "frequency": "15min",
            "direction": "both",
            "stage": "energy",
            "metric": "marginal_price",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) == 192,
        (
            "Expected 192 PT aFRR "
            "display points, "
            f"got {len(rows)}."
        ),
    )

    assert_true(
        all(
            row.get(
                "native_resolution_minutes"
            ) == 60
            for row in rows
        ),
        (
            "PT aFRR native resolution "
            "should be 60 minutes."
        ),
    )

    assert_true(
        all(
            bool(
                row.get("is_upsampled")
            )
            for row in rows
        ),
        (
            "Every PT aFRR point should be "
            "marked as upsampled at 15-minute "
            "display frequency."
        ),
    )

    assert_true(
        {
            row.get("direction")
            for row in rows
        } == {
            "up",
            "down",
        },
        (
            "PT aFRR response should "
            "contain UP and DOWN."
        ),
    )

    print(
        f"    Display points: {len(rows)}"
    )

    print(
        "    Native resolution: 60 min"
    )

    print(
        "    All points correctly marked "
        "as upsampled"
    )


# ============================================================
# 11. KNOWN REN aFRR GAP — 1–2 AUGUST 2026
#
# Official price fields are blank.
# Correct behavior = zero observations.
# ============================================================

def test_pt_afrr_known_gap() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "afrr",
            "country": "PT",
            "start_date": "2026-08-01",
            "end_date": "2026-08-02",
            "frequency": "15min",
            "direction": "both",
            "stage": "energy",
            "metric": "marginal_price",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) == 0,
        (
            "Known REN gap should return "
            "zero observations. "
            f"Got {len(rows)} rows."
        ),
    )

    print(
        "    Correctly returned no "
        "fabricated observations"
    )


# ============================================================
# 12. SPAIN mFRR — SCHEDULED WEIGHTED-AVERAGE PRICE
# ============================================================

def test_es_mfrr_scheduled() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "mfrr",
            "country": "ES",
            "start_date": "2026-08-03",
            "end_date": "2026-08-03",
            "frequency": "15min",
            "direction": "both",
            "stage": "energy_scheduled",
            "metric": "weighted_average_price",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) > 0,
        (
            "ES scheduled mFRR returned "
            "no observations."
        ),
    )

    assert_true(
        all(
            row.get("country") == "ES"
            for row in rows
        ),
        (
            "Unexpected country in "
            "ES mFRR response."
        ),
    )

    assert_true(
        all(
            row.get("unit") == "EUR/MWh"
            for row in rows
        ),
        "Unexpected ES mFRR unit.",
    )

    directions = {
        row.get("direction")
        for row in rows
    }

    assert_true(
        {
            "up",
            "down",
        }.issubset(
            directions
        ),
        (
            "Expected both UP and DOWN, "
            f"got {directions}."
        ),
    )

    print(
        f"    Display points: {len(rows)}"
    )

    print(
        f"    Directions: "
        f"{sorted(directions)}"
    )


# ============================================================
# 13. PORTUGAL mFRR — SCHEDULED ACTIVATION PRICE
#
# Missing official values are allowed; no fabrication.
# ============================================================

def test_pt_mfrr_scheduled() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "mfrr",
            "country": "PT",
            "start_date": "2026-08-03",
            "end_date": "2026-08-03",
            "frequency": "15min",
            "direction": "both",
            "stage": "energy_scheduled",
            "metric": "scheduled_activation_price",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) > 0,
        (
            "PT scheduled mFRR returned "
            "no observations."
        ),
    )

    assert_true(
        all(
            row.get("country") == "PT"
            for row in rows
        ),
        (
            "Unexpected country in "
            "PT mFRR response."
        ),
    )

    assert_true(
        all(
            row.get("unit") == "EUR/MWh"
            for row in rows
        ),
        "Unexpected PT mFRR unit.",
    )

    directions = {
        row.get("direction")
        for row in rows
    }

    assert_true(
        {
            "up",
            "down",
        }.issubset(
            directions
        ),
        (
            "Expected UP and DOWN, "
            f"got {directions}."
        ),
    )

    assert_true(
        len(rows) <= 192,
        (
            "PT scheduled mFRR returned "
            "more observations than possible "
            "for one 15-minute day with "
            "two directions."
        ),
    )

    print(
        f"    Display points: {len(rows)}"
    )

    print(
        f"    Directions: "
        f"{sorted(directions)}"
    )

    if len(rows) < 192:
        print(
            "    Missing official source "
            "values correctly remain absent"
        )


# ============================================================
# 14. PORTUGAL RR — LEGACY SERIES
# ============================================================

def test_pt_rr_legacy() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "rr",
            "country": "PT",
            "start_date": "2025-04-14",
            "end_date": "2025-04-15",
            "frequency": "1h",
            "stage": "energy_legacy",
            "metric": "activation_price",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) > 0,
        (
            "Legacy PT RR returned "
            "no data."
        ),
    )

    assert_true(
        all(
            row.get("country") == "PT"
            for row in rows
        ),
        (
            "Unexpected country "
            "in legacy RR."
        ),
    )

    assert_true(
        all(
            row.get("unit") == "EUR/MWh"
            for row in rows
        ),
        (
            "Unexpected unit "
            "in legacy RR."
        ),
    )

    print(
        f"    Legacy RR points: "
        f"{len(rows)}"
    )


# ============================================================
# 15. PORTUGAL RR — NEW SERIES
# ============================================================

def test_pt_rr_current() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "rr",
            "country": "PT",
            "start_date": "2025-04-16",
            "end_date": "2025-04-18",
            "frequency": "15min",
            "stage": "energy",
            "metric": "activation_price",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) > 0,
        (
            "Modern PT RR returned "
            "no data."
        ),
    )

    assert_true(
        all(
            row.get("country") == "PT"
            for row in rows
        ),
        (
            "Unexpected country "
            "in modern RR."
        ),
    )

    assert_true(
        all(
            row.get("unit") == "EUR/MWh"
            for row in rows
        ),
        (
            "Unexpected unit "
            "in modern RR."
        ),
    )

    print(
        f"    Modern RR points: "
        f"{len(rows)}"
    )


# ============================================================
# 16. CONTINUOUS-INTRADAY KNOWN SOURCE GAP
#
# OMIE file for 2025-04-29 was unavailable.
# Correct behavior = no fabricated values.
# ============================================================

def test_continuous_known_gap() -> None:
    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "intraday_continuous",
            "country": "ES",
            "start_date": "2025-04-29",
            "end_date": "2025-04-29",
            "frequency": "15min",
        },
    )

    print_timing(elapsed)

    rows = data_rows(payload)

    assert_true(
        len(rows) == 0,
        (
            "Known continuous-intraday "
            "source gap should return "
            "zero observations, "
            f"got {len(rows)}."
        ),
    )

    print(
        "    Correctly preserved "
        "official source gap"
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

def main() -> int:
    print()
    print(
        "Iberian Energy Data Hub"
    )

    print(
        "Local API Smoke Test"
    )

    print(
        f"API: {BASE_URL}"
    )

    tests = [
        (
            "1. FastAPI health endpoint",
            test_health,
        ),
        (
            "2. Market catalog",
            test_catalog,
        ),
        (
            "3. Day-ahead ES: QH → hourly aggregation",
            test_day_ahead_es_hourly,
        ),
        (
            "4. Day-ahead ES + PT: hourly",
            test_day_ahead_both_hourly,
        ),
        (
            "5. Day-ahead 2025 resolution transition",
            test_day_ahead_resolution_transition,
        ),
        (
            "6. Intraday auction session 1: three complete days",
            test_intraday_auction_session_1_complete_days,
        ),
        (
            "7. Intraday auction known empty official files",
            test_intraday_auction_known_empty_files,
        ),
        (
            "8. Continuous intraday ES + PT",
            test_intraday_continuous_both,
        ),
        (
            "9. Spain aFRR energy",
            test_es_afrr_energy,
        ),
        (
            "10. Portugal aFRR hourly → 15-minute display",
            test_pt_afrr_hourly_to_quarter_hour,
        ),
        (
            "11. Portugal aFRR known official gap",
            test_pt_afrr_known_gap,
        ),
        (
            "12. Spain scheduled mFRR",
            test_es_mfrr_scheduled,
        ),
        (
            "13. Portugal scheduled mFRR",
            test_pt_mfrr_scheduled,
        ),
        (
            "14. Portugal RR legacy",
            test_pt_rr_legacy,
        ),
        (
            "15. Portugal RR modern",
            test_pt_rr_current,
        ),
        (
            "16. Continuous intraday known source gap",
            test_continuous_known_gap,
        ),
    ]

    for name, test_function in tests:
        run_test(
            name,
            test_function,
        )

    print()
    print("=" * 72)
    print("FINAL RESULT")
    print("=" * 72)

    print(
        f"Passed:   {passed}"
    )

    print(
        f"Failed:   {failed}"
    )

    print(
        f"Warnings: {warnings}"
    )

    print()

    if failed == 0:
        print(
            "SMOKE TEST PASSED"
        )
        return 0

    print(
        "SMOKE TEST FAILED"
    )

    return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )