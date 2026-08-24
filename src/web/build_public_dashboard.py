from __future__ import annotations

from pathlib import Path


# ============================================================
# PATHS
# ============================================================

REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

SOURCE_PATH = (
    REPO_ROOT
    / "src"
    / "web"
    / "index.html"
)

OUTPUT_PATH = (
    REPO_ROOT
    / "src"
    / "web"
    / "public_index.html"
)


# ============================================================
# PUBLIC PRICE SERIES
# ============================================================

PUBLIC_SERIES_BLOCK = """    const SERIES = [

        {
            id: "day_ahead",
            group: "Wholesale",
            label: "Day-ahead price",
            market: "day_ahead",
            stage: "energy",
            metric: null,
            direction: false,
            session: false
        },

        {
            id: "intraday_auction",
            group: "Wholesale",
            label: "Intraday auction price",
            market: "intraday_auction",
            stage: "energy",
            metric: null,
            direction: false,
            session: true
        },

        {
            id: "intraday_continuous",
            group: "Wholesale",
            label: "Continuous intraday weighted-average price",
            market: "intraday_continuous",
            stage: "energy",
            metric: null,
            direction: false,
            session: false
        }

    ];"""


# ============================================================
# PUBLIC DATA GUIDE
# ============================================================

PUBLIC_DATA_GUIDE = """
    <section class="panel">

        <details
            style="
                margin-top: 0;
                border-top: 0;
                padding-top: 0;
            "
        >

            <summary>
                Price series &amp; frequency methodology
            </summary>


            <div
                style="
                    margin-top: 18px;
                    color: #475467;
                    font-size: 13px;
                    line-height: 1.6;
                "
            >

                <p style="margin-top: 0;">
                    This guide explains what each displayed price represents
                    and how the selected display frequency is calculated.
                    Original OMIE observations are preserved in the database.
                    Display transformations do not modify the source data.
                </p>


                <h3
                    style="
                        margin: 22px 0 10px;
                        color: #182230;
                        font-size: 15px;
                    "
                >
                    Price series
                </h3>


                <div style="overflow-x: auto;">

                    <table
                        style="
                            white-space: normal;
                            min-width: 760px;
                        "
                    >

                        <thead>

                            <tr>
                                <th>Price series</th>
                                <th>What it represents</th>
                                <th>Unit</th>
                            </tr>

                        </thead>


                        <tbody>

                            <tr>

                                <td>
                                    <strong>
                                        Day-ahead price
                                    </strong>
                                </td>

                                <td>
                                    OMIE day-ahead market-clearing price for
                                    each electricity delivery period and
                                    bidding zone. Spain and Portugal are shown
                                    separately when both are selected.
                                </td>

                                <td>
                                    EUR/MWh
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <strong>
                                        Intraday auction price
                                    </strong>
                                </td>

                                <td>
                                    OMIE clearing price for the selected
                                    intraday auction session and electricity
                                    delivery period. Auction sessions are kept
                                    separate because each session is a distinct
                                    market-clearing process.
                                </td>

                                <td>
                                    EUR/MWh
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <strong>
                                        Continuous intraday
                                        weighted-average price
                                    </strong>
                                </td>

                                <td>
                                    Volume-weighted average price of continuous
                                    intraday trades for each electricity
                                    delivery period.
                                </td>

                                <td>
                                    EUR/MWh
                                </td>

                            </tr>

                        </tbody>

                    </table>

                </div>


                <h3
                    style="
                        margin: 24px 0 10px;
                        color: #182230;
                        font-size: 15px;
                    "
                >
                    Display frequency
                </h3>


                <div style="overflow-x: auto;">

                    <table
                        style="
                            white-space: normal;
                            min-width: 820px;
                        "
                    >

                        <thead>

                            <tr>
                                <th>Frequency</th>
                                <th>How the displayed value is calculated</th>
                            </tr>

                        </thead>


                        <tbody>

                            <tr>

                                <td>
                                    <strong>
                                        15 minutes
                                    </strong>
                                </td>

                                <td>
                                    Native 15-minute prices are shown unchanged.
                                    When the official source is hourly, the
                                    hourly value is repeated at HH:00, HH:15,
                                    HH:30 and HH:45. This is a display
                                    transformation only: it is not interpolation
                                    and does not create a new market price.
                                    These repeated sections are shown with a
                                    dashed line.
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <strong>
                                        Hourly
                                    </strong>
                                </td>

                                <td>
                                    Native hourly observations are shown
                                    unchanged. Native 15-minute observations
                                    within each hour are aggregated using a
                                    time-weighted mean.
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <strong>
                                        Daily
                                    </strong>
                                </td>

                                <td>
                                    Time-weighted mean of the available official
                                    observations within each market day.
                                    Calendar boundaries use MIBEL market time.
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <strong>
                                        Weekly
                                    </strong>
                                </td>

                                <td>
                                    Time-weighted mean of the available official
                                    observations in each Monday-to-Sunday week,
                                    using MIBEL market time.
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <strong>
                                        Monthly
                                    </strong>
                                </td>

                                <td>
                                    Time-weighted mean of the available official
                                    observations within each calendar month,
                                    using MIBEL market time.
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <strong>
                                        Yearly
                                    </strong>
                                </td>

                                <td>
                                    Time-weighted mean of the available official
                                    observations within each calendar year,
                                    using MIBEL market time.
                                </td>

                            </tr>

                        </tbody>

                    </table>

                </div>


                <div
                    style="
                        margin-top: 18px;
                        padding: 13px 14px;
                        border-radius: 7px;
                        background: #f8fafc;
                    "
                >

                    <strong>
                        Why time-weighted?
                    </strong>

                    A 60-minute source observation represents four times as
                    much time as a 15-minute observation. Weighting each value
                    by its native duration prevents periods with finer
                    resolution from receiving disproportionate weight when
                    historical datasets contain different native resolutions.

                </div>


                <div
                    style="
                        margin-top: 10px;
                        padding: 13px 14px;
                        border-radius: 7px;
                        background: #f8fafc;
                    "
                >

                    <strong>
                        Missing data.
                    </strong>

                    Missing official observations are kept missing. The
                    application does not replace missing prices with zero and
                    does not interpolate across official source gaps.

                </div>


                <p
                    style="
                        margin-bottom: 0;
                        margin-top: 16px;
                        color: #667085;
                        font-size: 12px;
                    "
                >
                    Source: OMIE. Market-time calculations use
                    Europe/Madrid, consistent with the MIBEL market clock.
                </p>

            </div>

        </details>

    </section>
"""


# ============================================================
# REPLACE SERIES
# ============================================================

def replace_series_block(
    html: str,
) -> str:

    start_marker = (
        "    const SERIES = ["
    )

    end_marker = (
        "\n    ];"
    )

    start_index = html.find(
        start_marker
    )

    if start_index == -1:

        raise RuntimeError(
            "Could not find SERIES block start."
        )

    end_index = html.find(
        end_marker,
        start_index,
    )

    if end_index == -1:

        raise RuntimeError(
            "Could not find SERIES block end."
        )

    end_index += len(
        end_marker
    )

    return (
        html[:start_index]
        + PUBLIC_SERIES_BLOCK
        + html[end_index:]
    )


# ============================================================
# PUBLIC CACHE KEY
# ============================================================

def replace_cache_key(
    html: str,
) -> str:

    old = (
        '"iberian_energy_market_catalog_v1"'
    )

    new = (
        '"iberian_energy_public_market_catalog_v1"'
    )

    if old not in html:

        raise RuntimeError(
            "Could not find catalog cache key."
        )

    return html.replace(
        old,
        new,
        1,
    )


# ============================================================
# PUBLIC SUBTITLE
# ============================================================

def replace_subtitle(
    html: str,
) -> str:

    old = (
        "Historical electricity-market prices "
        "for Spain and Portugal"
    )

    new = (
        "Public OMIE electricity-market data "
        "for Spain and Portugal"
    )

    if old not in html:

        raise RuntimeError(
            "Could not find dashboard subtitle."
        )

    return html.replace(
        old,
        new,
        1,
    )


# ============================================================
# PUBLIC PORTFOLIO NOTE
# ============================================================

def add_public_note(
    html: str,
) -> str:

    marker = (
        "<main>"
    )

    note = """
<main>

    <section class="panel">

        <div
            class="note"
            style="
                margin-top: 0;
                padding-top: 0;
                border-top: 0;
            "
        >

            <strong>
                Public portfolio demo.
            </strong>

            This version exposes historical OMIE wholesale-market data only:
            day-ahead, intraday auctions and continuous intraday prices for
            Spain and Portugal. The local research project also contains
            additional Iberian market datasets that are not redistributed
            through this public demo.

        </div>

    </section>
"""

    if marker not in html:

        raise RuntimeError(
            "Could not find <main> element."
        )

    return html.replace(
        marker,
        note,
        1,
    )


# ============================================================
# ADD DATA GUIDE
# ============================================================

def add_data_guide(
    html: str,
) -> str:

    marker = """
    <section class="panel">

        <h2 class="panel-title">
            Price explorer
        </h2>
"""

    if marker not in html:

        raise RuntimeError(
            (
                "Could not find Price explorer "
                "section for guide insertion."
            )
        )

    return html.replace(
        marker,
        (
            PUBLIC_DATA_GUIDE
            + "\n"
            + marker
        ),
        1,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_output(
    html: str,
) -> None:

    forbidden_terms = [
        'id: "afrr_',
        'id: "mfrr_',
        'id: "rr_',
    ]

    for term in forbidden_terms:

        if term in html:

            raise RuntimeError(
                (
                    "Public dashboard still "
                    f"contains forbidden series: {term}"
                )
            )


    required_terms = [
        'id: "day_ahead"',
        'id: "intraday_auction"',
        'id: "intraday_continuous"',
        "Public portfolio demo.",
        "Price series &amp; frequency methodology",
        "Why time-weighted?",
        "Missing official observations are kept missing.",
        "iberian_energy_public_market_catalog_v1",
    ]

    for term in required_terms:

        if term not in html:

            raise RuntimeError(
                (
                    "Generated public dashboard "
                    f"is missing required content: {term}"
                )
            )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print()
    print("=" * 72)
    print(
        "BUILD PUBLIC DASHBOARD"
    )
    print("=" * 72)
    print()


    if not SOURCE_PATH.exists():

        raise FileNotFoundError(
            (
                "Local dashboard not found: "
                f"{SOURCE_PATH}"
            )
        )


    html = SOURCE_PATH.read_text(
        encoding="utf-8"
    )


    html = replace_series_block(
        html
    )

    html = replace_cache_key(
        html
    )

    html = replace_subtitle(
        html
    )

    html = add_public_note(
        html
    )

    html = add_data_guide(
        html
    )


    validate_output(
        html
    )


    OUTPUT_PATH.write_text(
        html,
        encoding="utf-8",
    )


    print(
        f"Source: {SOURCE_PATH}"
    )

    print(
        f"Output: {OUTPUT_PATH}"
    )

    print()


    print(
        "Public price series:"
    )

    print(
        "  - Day-ahead"
    )

    print(
        "  - Intraday auction"
    )

    print(
        "  - Continuous intraday"
    )

    print()


    print(
        "Methodology guide:"
    )

    print(
        "  - Price-series definitions"
    )

    print(
        "  - 15-minute display method"
    )

    print(
        "  - Hourly aggregation"
    )

    print(
        "  - Daily aggregation"
    )

    print(
        "  - Weekly aggregation"
    )

    print(
        "  - Monthly aggregation"
    )

    print(
        "  - Yearly aggregation"
    )

    print(
        "  - Missing-data policy"
    )

    print()


    print(
        "Balancing-market selectors: excluded"
    )

    print(
        "Public browser cache: separate"
    )


    print()
    print("=" * 72)
    print(
        "PUBLIC DASHBOARD BUILD PASSED"
    )
    print("=" * 72)


if __name__ == "__main__":

    main()