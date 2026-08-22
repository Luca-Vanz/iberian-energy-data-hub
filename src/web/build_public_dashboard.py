from __future__ import annotations

from pathlib import Path


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


def add_public_note(
    html: str,
) -> str:

    marker = (
        '<main>'
    )

    note = """
<main>

    <section class="panel">

        <div class="note" style="margin-top: 0; padding-top: 0; border-top: 0;">
            <strong>Public portfolio demo.</strong>
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