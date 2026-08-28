from __future__ import annotations

import sys
import time
from typing import Any

import requests


BASE_URL = "http://127.0.0.1:8001"
TIMEOUT_SECONDS = 30

ALLOWED_PUBLIC_MARKETS = {
    "day_ahead",
    "intraday_auction",
    "intraday_continuous",
}

ALLOWED_PUBLIC_BALANCING_MARKETS = {
    "afrr",
    "mfrr",
    "rr",
}

FORBIDDEN_PUBLIC_MARKETS = set()


passed = 0
failed = 0
warnings = 0


class SmokeTestFailure(AssertionError):
    pass


def assert_true(
    condition: bool,
    message: str,
) -> None:

    if not condition:
        raise SmokeTestFailure(
            message
        )


def request(
    path: str,
    params: dict[str, Any] | None = None,
) -> tuple[requests.Response, float]:

    start = time.perf_counter()

    response = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        timeout=TIMEOUT_SECONDS,
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    return response, elapsed


def request_json(
    path: str,
    params: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> tuple[dict[str, Any], float]:

    response, elapsed = request(
        path,
        params,
    )

    assert_true(
        response.status_code
        == expected_status,
        (
            f"Expected HTTP {expected_status}, "
            f"got {response.status_code} "
            f"from {response.url}\n"
            f"Response: {response.text[:1000]}"
        ),
    )

    try:

        payload = response.json()

    except ValueError as exc:

        raise SmokeTestFailure(
            (
                "Expected JSON response from "
                f"{response.url}."
            )
        ) from exc

    return payload, elapsed


def print_timing(
    elapsed: float,
) -> None:

    global warnings

    print(
        f"    API time: {elapsed:.3f} s"
    )

    if elapsed > 2:

        warnings += 1

        print(
            "    WARNING: request took "
            "more than 2 seconds"
        )


def run_test(
    name: str,
    function,
) -> None:

    global passed
    global failed

    print()
    print("=" * 72)
    print(name)
    print("=" * 72)

    try:

        function()

    except Exception as exc:

        failed += 1

        print(
            f"FAIL: {exc}"
        )

    else:

        passed += 1

        print(
            "PASS"
        )


# ============================================================
# 1. HEALTH / MODE
# ============================================================

def test_health_public_mode() -> None:

    payload, elapsed = request_json(
        "/health"
    )

    print_timing(
        elapsed
    )

    assert_true(
        payload.get("status")
        == "ok",
        (
            "Unexpected health status: "
            f"{payload}"
        ),
    )

    assert_true(
        payload.get("mode")
        == "public",
        (
            "Application is not running "
            "in public mode. "
            f"Response: {payload}"
        ),
    )

    print(
        "    Mode: public"
    )


# ============================================================
# 2. PUBLIC DASHBOARD
# ============================================================

def test_public_dashboard() -> None:

    response, elapsed = request(
        "/"
    )

    print_timing(
        elapsed
    )

    assert_true(
        response.status_code
        == 200,
        (
            "Public dashboard returned "
            f"HTTP {response.status_code}."
        ),
    )

    html = response.text

    assert_true(
        "Public portfolio demo."
        in html,
        (
            "Root page does not appear "
            "to be public_index.html."
        ),
    )

    assert_true(
        'id: "day_ahead"'
        in html,
        (
            "Public dashboard is missing "
            "day-ahead series."
        ),
    )

    assert_true(
        'id: "intraday_auction"'
        in html,
        (
            "Public dashboard is missing "
            "intraday auction series."
        ),
    )

    assert_true(
        'id: "intraday_continuous"'
        in html,
        (
            "Public dashboard is missing "
            "continuous intraday series."
        ),
    )

    required_balancing_strings = [
        'id: "afrr_energy_marginal"',
        'id: "afrr_capacity_marginal"',
        'id: "afrr_capacity_weighted"',
        'id: "mfrr_scheduled_weighted_es"',
        'id: "mfrr_scheduled_market_es"',
        'id: "mfrr_direct_weighted_es"',
        'id: "mfrr_legacy_es"',
        'id: "rr_activation_pt"',
        "Public REE/ESIOS price series.",
    ]

    for required in required_balancing_strings:

        assert_true(
            required in html,
            (
                "Public dashboard is missing "
                f"REE/ESIOS content: {required}"
            ),
        )

    forbidden_strings = []

    for forbidden in forbidden_strings:

        assert_true(
            forbidden not in html,
            (
                "Public dashboard contains "
                f"forbidden balancing selector: "
                f"{forbidden}"
            ),
        )

    required_download_features = [
        "Download data",
        "Download selected range as CSV",
        "Select full available range",
        "Chart range limits",
        "do not apply to the CSV download.",
        "Preview exact data values",
        "function buildDownloadChunks()",
        "function buildRequestChunks(",
        "function calendarYearChunks(",
        "function weeklyChunks(",
        "function noDataCoverageMessage()",
        "Available series —",
        "native ${resolutions}",
        "The data service is temporarily unavailable.",
    ]

    required_loading_features = [
        'id="chartLoading"',
        "Crunching the megawatts...",
        "larger data selections can take a little",
        'role="status"',
    ]

    for required in required_loading_features:

        assert_true(
            required in html,
            (
                "Public dashboard is missing "
                f"the graph loading state: {required}"
            ),
        )

    for required in required_download_features:

        assert_true(
            required in html,
            (
                "Public dashboard is missing "
                "the unrestricted download feature: "
                f"{required}"
            ),
        )

    ordered_sections = [
        "Price explorer",
        "Download data",
        "Price chart",
        "Price series &amp; frequency methodology",
        "Market evolution storyline",
        "Data coverage &amp; quality",
    ]

    positions = [
        html.find(section)
        for section in ordered_sections
    ]

    assert_true(
        positions == sorted(positions),
        (
            "Public dashboard sections are not "
            f"in the expected order: {ordered_sections}"
        ),
    )

    assert_true(
        html.find("Preview exact data values")
        < html.find("Price chart"),
        (
            "Exact-value preview should appear in "
            "the Download data section."
        ),
    )

    print(
        "    OMIE wholesale and REE/ESIOS "
        "balancing selectors with full-range downloads"
    )


# ============================================================
# 3. ABOUT
# ============================================================

def test_about() -> None:

    payload, elapsed = request_json(
        "/about"
    )

    print_timing(
        elapsed
    )

    assert_true(
        payload.get("public_demo")
        is True,
        (
            "About endpoint does not "
            "identify public mode."
        ),
    )

    sources = set(
        payload.get(
            "sources",
            [],
        )
    )

    assert_true(
        sources == {"OMIE", "ESIOS", "REN"},
        (
            "Unexpected public sources: "
            f"{sources}"
        ),
    )

    markets = set(
        payload.get(
            "markets",
            [],
        )
    )

    expected_markets = {
        "Day-ahead",
        "Intraday auctions",
        "Continuous intraday",
        "aFRR",
        "mFRR",
        "RR",
    }

    assert_true(
        markets == expected_markets,
        (
            "Unexpected public markets: "
            f"{markets}"
        ),
    )

    print(
        "    Sources: OMIE, ESIOS and REN"
    )


# ============================================================
# 4. PUBLIC MARKET CATALOG
# ============================================================

def test_catalog() -> None:

    payload, elapsed = request_json(
        "/market/catalog"
    )

    print_timing(
        elapsed
    )

    wholesale = payload.get(
        "wholesale",
        [],
    )

    balancing = payload.get(
        "balancing",
        [],
    )

    assert_true(
        len(balancing) == 15,
        (
            "Expected 15 approved balancing "
            f"catalog rows, got {len(balancing)}."
        ),
    )

    assert_true(
        {
            row.get("market")
            for row in balancing
        } == ALLOWED_PUBLIC_BALANCING_MARKETS,
        "Unexpected public balancing markets.",
    )

    assert_true(
        all(
            (
                row.get("source") == "ESIOS"
                and row.get("country") == "ES"
                and row.get("market") in {"afrr", "mfrr"}
            )
            or (
                row.get("source") == "REN"
                and row.get("country") == "PT"
                and row.get("market") == "rr"
            )
            for row in balancing
        ),
        "Public catalog contains an unapproved balancing row.",
    )

    assert_true(
        len(wholesale) == 16,
        (
            "Expected 16 wholesale "
            f"catalog rows, got "
            f"{len(wholesale)}."
        ),
    )

    markets = {
        row.get("market")
        for row in wholesale
    }

    assert_true(
        markets.issubset(
            ALLOWED_PUBLIC_MARKETS
        ),
        (
            "Public catalog contains "
            f"unexpected markets: "
            f"{markets}"
        ),
    )

    assert_true(
        markets
        == ALLOWED_PUBLIC_MARKETS,
        (
            "Public catalog is missing "
            f"wholesale markets: "
            f"{ALLOWED_PUBLIC_MARKETS - markets}"
        ),
    )

    print(
        f"    Wholesale catalog rows: "
        f"{len(wholesale)}"
    )

    print(
        f"    Balancing catalog rows: {len(balancing)}"
    )


# ============================================================
# 5. DAY-AHEAD
# ============================================================

def test_day_ahead() -> None:

    payload, elapsed = request_json(
        "/market/prices",
        {
            "market":
                "day_ahead",

            "country":
                "both",

            "start_date":
                "2026-08-03",

            "end_date":
                "2026-08-03",

            "frequency":
                "1h",
        },
    )

    print_timing(
        elapsed
    )

    rows = payload.get(
        "data",
        [],
    )

    assert_true(
        len(rows) == 48,
        (
            "Expected 48 public "
            "day-ahead display points, "
            f"got {len(rows)}."
        ),
    )

    sources = {
        row.get("source")
        for row in rows
    }

    assert_true(
        sources == {"OMIE"},
        (
            "Unexpected source in "
            f"public day-ahead data: "
            f"{sources}"
        ),
    )

    print(
        "    Day-ahead ES + PT: 48 points"
    )


# ============================================================
# 6. INTRADAY AUCTION
# ============================================================

def test_intraday_auction() -> None:

    payload, elapsed = request_json(
        "/market/prices",
        {
            "market":
                "intraday_auction",

            "country":
                "ES",

            "start_date":
                "2026-08-01",

            "end_date":
                "2026-08-01",

            "frequency":
                "15min",

            "session":
                1,
        },
    )

    print_timing(
        elapsed
    )

    rows = payload.get(
        "data",
        [],
    )

    assert_true(
        len(rows) == 96,
        (
            "Expected 96 public "
            "intraday-auction points, "
            f"got {len(rows)}."
        ),
    )

    assert_true(
        {
            row.get("source")
            for row in rows
        } == {"OMIE"},
        (
            "Unexpected source in "
            "public auction data."
        ),
    )

    print(
        "    Intraday auction: 96 points"
    )


# ============================================================
# 7. CONTINUOUS INTRADAY
# ============================================================

def test_intraday_continuous() -> None:

    payload, elapsed = request_json(
        "/market/prices",
        {
            "market":
                "intraday_continuous",

            "country":
                "both",

            "start_date":
                "2026-08-03",

            "end_date":
                "2026-08-03",

            "frequency":
                "15min",
        },
    )

    print_timing(
        elapsed
    )

    rows = payload.get(
        "data",
        [],
    )

    assert_true(
        len(rows) == 192,
        (
            "Expected 192 public "
            "continuous-intraday points, "
            f"got {len(rows)}."
        ),
    )

    assert_true(
        {
            row.get("source")
            for row in rows
        } == {"OMIE"},
        (
            "Unexpected source in "
            "continuous-intraday data."
        ),
    )

    print(
        "    Continuous intraday "
        "ES + PT: 192 points"
    )


# ============================================================
# 8–9. APPROVED REE/ESIOS BALANCING MARKETS
# ============================================================

def test_public_afrr() -> None:

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
    rows = payload.get("data", [])

    assert_true(
        len(rows) == 192,
        f"Expected 192 public aFRR rows, got {len(rows)}.",
    )
    assert_true(
        {row.get("source") for row in rows} == {"ESIOS"},
        "Unexpected public aFRR source.",
    )
    assert_true(
        {row.get("direction") for row in rows} == {"up", "down"},
        "Unexpected public aFRR directions.",
    )


def test_public_mfrr() -> None:

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
    rows = payload.get("data", [])

    assert_true(
        len(rows) > 0,
        "Public mFRR returned no rows.",
    )
    assert_true(
        {row.get("source") for row in rows} == {"ESIOS"},
        "Unexpected public mFRR source.",
    )
    assert_true(
        {"up", "down"}.issubset(
            {row.get("direction") for row in rows}
        ),
        "Expected both public mFRR directions.",
    )


# ============================================================
# 10. PUBLIC REN RR
# ============================================================

def test_forbidden_market(
    market: str,
) -> None:

    payload, elapsed = request_json(
        "/market/prices",
        {
            "market":
                market,

            "country":
                "ES",

            "start_date":
                "2026-08-03",

            "end_date":
                "2026-08-03",

            "frequency":
                "15min",
        },
        expected_status=403,
    )

    print_timing(
        elapsed
    )

    assert_true(
        (
            "not available"
            in str(
                payload.get(
                    "detail",
                    "",
                )
            ).lower()
        ),
        (
            "403 response did not contain "
            "the expected public-access message."
        ),
    )

    print(
        f"    {market}: correctly blocked"
    )


def test_public_rr() -> None:

    payload, elapsed = request_json(
        "/market/prices",
        {
            "market": "rr",
            "country": "PT",
            "start_date": "2025-04-16",
            "end_date": "2025-04-16",
            "frequency": "15min",
            "direction": "none",
            "stage": "energy",
            "metric": "activation_price",
        },
    )

    print_timing(elapsed)
    rows = payload.get("data", [])

    assert_true(
        len(rows) > 0,
        "Public RR returned no rows.",
    )
    assert_true(
        {row.get("source") for row in rows} == {"REN"},
        "Unexpected public RR source.",
    )
    assert_true(
        {row.get("country") for row in rows} == {"PT"},
        "Unexpected public RR country.",
    )
    assert_true(
        {
            row.get("native_resolution_minutes")
            for row in rows
        } == {15},
        "Unexpected public RR native resolution.",
    )

    legacy_payload, legacy_elapsed = request_json(
        "/market/prices",
        {
            "market": "rr",
            "country": "PT",
            "start_date": "2025-04-15",
            "end_date": "2025-04-15",
            "frequency": "15min",
            "direction": "none",
            "stage": "energy_legacy",
            "metric": "activation_price",
        },
    )

    print_timing(legacy_elapsed)
    legacy_rows = legacy_payload.get("data", [])

    assert_true(
        len(legacy_rows) > 0,
        "Public legacy RR returned no rows.",
    )
    assert_true(
        {row.get("source") for row in legacy_rows} == {"REN"},
        "Unexpected public legacy RR source.",
    )
    assert_true(
        {
            row.get("native_resolution_minutes")
            for row in legacy_rows
        } == {60},
        "Unexpected public legacy RR native resolution.",
    )


# ============================================================
# 11. DASHBOARD ALIAS
# ============================================================

def test_dashboard_alias() -> None:

    response, elapsed = request(
        "/dashboard"
    )

    print_timing(
        elapsed
    )

    assert_true(
        response.status_code
        == 200,
        (
            "/dashboard returned "
            f"HTTP {response.status_code}."
        ),
    )

    assert_true(
        "Public portfolio demo."
        in response.text,
        (
            "/dashboard is not serving "
            "the public dashboard."
        ),
    )


# ============================================================
# RUN
# ============================================================

def main() -> int:

    print()
    print(
        "Iberian Energy Data Hub"
    )

    print(
        "PUBLIC MODE SMOKE TEST"
    )

    print(
        f"API: {BASE_URL}"
    )


    tests = [

        (
            "1. Health reports public mode",
            test_health_public_mode,
        ),

        (
            "2. Public dashboard exposes approved price series",
            test_public_dashboard,
        ),

        (
            "3. About endpoint is public-safe",
            test_about,
        ),

        (
            "4. Public catalog is source-restricted",
            test_catalog,
        ),

        (
            "5. Public day-ahead prices",
            test_day_ahead,
        ),

        (
            "6. Public intraday auction",
            test_intraday_auction,
        ),

        (
            "7. Public continuous intraday",
            test_intraday_continuous,
        ),

        (
            "8. Public REE/ESIOS aFRR",
            test_public_afrr,
        ),

        (
            "9. Public REE/ESIOS mFRR",
            test_public_mfrr,
        ),

        (
            "10. Public REN RR",
            test_public_rr,
        ),

        (
            "11. Dashboard alias is public-safe",
            test_dashboard_alias,
        ),
    ]


    for name, function in tests:

        run_test(
            name,
            function,
        )


    print()
    print("=" * 72)
    print(
        "FINAL RESULT"
    )
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
            "PUBLIC MODE SMOKE TEST PASSED"
        )

        return 0


    print(
        "PUBLIC MODE SMOKE TEST FAILED"
    )

    return 1


if __name__ == "__main__":

    sys.exit(
        main()
    )
