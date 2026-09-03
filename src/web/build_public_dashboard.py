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
        },

        {
            id: "afrr_energy_marginal",
            group: "REE/ESIOS aFRR",
            label: "aFRR energy — marginal price",
            market: "afrr",
            stage: "energy",
            metric: "marginal_price",
            direction: true,
            session: false,
            countries: ["ES"]
        },

        {
            id: "afrr_capacity_marginal",
            group: "REE/ESIOS aFRR",
            label: "aFRR capacity — marginal price",
            market: "afrr",
            stage: "capacity",
            metric: "marginal_price",
            direction: true,
            session: false,
            countries: ["ES"]
        },

        {
            id: "afrr_capacity_weighted",
            group: "REE/ESIOS aFRR",
            label: "aFRR capacity — weighted-average price",
            market: "afrr",
            stage: "capacity",
            metric: "weighted_average_price",
            direction: true,
            session: false,
            countries: ["ES"]
        },

        {
            id: "mfrr_scheduled_weighted_es",
            group: "REE/ESIOS mFRR",
            label: "mFRR scheduled — weighted-average price",
            market: "mfrr",
            stage: "energy_scheduled",
            metric: "weighted_average_price",
            direction: true,
            session: false,
            countries: ["ES"]
        },

        {
            id: "mfrr_scheduled_market_es",
            group: "REE/ESIOS mFRR",
            label: "mFRR scheduled — market price",
            market: "mfrr",
            stage: "energy_scheduled",
            metric: "market_price",
            direction: false,
            session: false,
            countries: ["ES"]
        },

        {
            id: "mfrr_direct_weighted_es",
            group: "REE/ESIOS mFRR",
            label: "mFRR direct — weighted-average price",
            market: "mfrr",
            stage: "energy_direct",
            metric: "weighted_average_price",
            direction: true,
            session: false,
            countries: ["ES"]
        },

        {
            id: "mfrr_legacy_es",
            group: "REE/ESIOS mFRR",
            label: "mFRR scheduled — legacy marginal price",
            market: "mfrr",
            stage: "energy_scheduled_legacy",
            metric: "marginal_price",
            direction: true,
            session: false,
            countries: ["ES"]
        },

        {
            id: "rr_activation_pt",
            group: "REN RR",
            label: "Replacement reserve — activation price",
            market: "rr",
            metric: "activation_price",
            direction: false,
            session: false,
            countries: ["PT"],
            availabilityMode: "union",

            components: [

                {
                    stage: "energy_legacy",
                    metric: "activation_price"
                },

                {
                    stage: "energy",
                    metric: "activation_price"
                }

            ]
        }

    ];"""

# Portuguese RR stays local until separately authorized. The RR definition is
# the final entry in the source selector block, so trim only that entry while
# preserving all validated Spanish REE/ESIOS aFRR and mFRR selectors.
_PORTUGUESE_RR_SERIES = '\n        {\n            id: "rr_activation_pt"'
PUBLIC_SERIES_BLOCK = (
    PUBLIC_SERIES_BLOCK.split(_PORTUGUESE_RR_SERIES, 1)[0].rstrip(",\n")
    + "\n\n    ];"
)


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
                    Original OMIE, REE/ESIOS and REN observations are preserved
                    in the database.
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
                                    The day-ahead market is the main auction in
                                    which electricity for every delivery period
                                    of the following day is bought and sold.
                                    OMIE matches the submitted supply and demand
                                    orders and calculates one clearing price for
                                    each delivery period and bidding zone. The
                                    value shown is that wholesale price: the
                                    amount paid per megawatt-hour of energy at
                                    the market-clearing point. It is not a
                                    household electricity tariff and does not
                                    include network charges, taxes or retail
                                    costs. Spain and Portugal are displayed as
                                    separate bidding zones because their prices
                                    can differ when cross-border capacity is
                                    constrained.
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
                                    Intraday auctions let market participants
                                    revise the positions they took in the
                                    day-ahead market as forecasts, demand or
                                    plant availability change closer to
                                    delivery. In each auction session, OMIE
                                    matches a new set of buy and sell orders.
                                    The displayed value is the resulting
                                    clearing price for the selected session,
                                    delivery period and bidding zone. It
                                    measures the price of energy in that
                                    specific auction, not a correction added to
                                    the day-ahead price. Sessions remain
                                    separate because the same delivery period
                                    can be traded and priced differently in
                                    several successive auctions.
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
                                    The continuous intraday market allows
                                    participants to buy and sell electricity
                                    continuously after the day-ahead market and
                                    between auction sessions, until closer to
                                    physical delivery. Unlike an auction, many
                                    bilateral trades can occur at different
                                    prices for the same delivery period. The
                                    displayed value is OMIE's
                                    volume-weighted average trade price: each
                                    transaction price is weighted by the amount
                                    of electricity traded, so larger trades
                                    influence the value more than smaller ones.
                                    It summarizes completed trades and is not a
                                    single market-clearing price.
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
                    Ancillary and balancing services
                </h3>


                <div
                    style="
                        padding: 14px 16px;
                        border: 1px solid #d0d5dd;
                        border-radius: 7px;
                        background: #f8fafc;
                    "
                >

                    <p style="margin-top: 0;">
                        <strong>
                            Public REE/ESIOS price series.
                        </strong>

                        Electricity must be balanced continuously: at every
                        moment, generation and imports must match consumption
                        and exports. Forecast errors, outages and changing
                        renewable output create a mismatch after the wholesale
                        markets have cleared. The system operator corrects
                        that mismatch by procuring reserve capacity in advance
                        and activating balancing energy when needed. These are
                        separate products from day-ahead and intraday energy
                        prices.
                    </p>

                    <p>
                        <strong>Up and down.</strong>
                        <em>Upward</em> means increasing net injection into
                        the system: a generator produces more, a consumer
                        reduces demand, or an importer increases imports.
                        <em>Downward</em> means reducing net injection: a
                        generator produces less, a consumer increases demand,
                        or an exporter increases exports. Up and down prices
                        are not positive and negative versions of one series;
                        they price opposite operational actions and must be
                        analysed separately.
                    </p>


                    <dl style="margin-bottom: 0;">

                        <dt>
                            <strong>
                                FCR — Frequency Containment Reserve
                            </strong>
                        </dt>

                        <dd style="margin: 3px 0 12px 20px;">
                            The fastest reserve layer. Participating resources
                            automatically change output or consumption within
                            seconds to contain an immediate frequency
                            deviation. No FCR price series is present in the
                            validated local price dataset, so none is shown.
                        </dd>


                        <dt>
                            <strong>
                                aFRR — automatic Frequency Restoration Reserve
                            </strong>
                        </dt>

                        <dd style="margin: 3px 0 12px 20px;">
                            aFRR is the automatic “fine correction” layer.
                            The control system sends an automatic signal to
                            participating resources to restore frequency and
                            the area balance over minutes. <strong>Energy
                            price</strong> is the price of the activated
                            electricity (EUR/MWh). <strong>Capacity
                            price</strong> is the payment for keeping response
                            capability available (EUR/MW), whether or not it
                            is later activated. “Marginal” means the price of
                            the last accepted offer; “weighted-average” means
                            the awarded quantities are used as weights. Up and
                            down are separate directions. In the validated
                            Spanish history, aFRR energy marginal prices are
                            hourly through 23 May 2022 and quarter-hourly from
                            24 May 2022.
                        </dd>


                        <dt>
                            <strong>
                                mFRR — manual Frequency Restoration Reserve
                            </strong>
                        </dt>

                        <dd style="margin: 3px 0 12px 20px;">
                            mFRR is the slower, manually dispatched layer used
                            for a sustained correction after the automatic
                            response. An operator selects bids to increase or
                            decrease generation or demand. <strong>Scheduled
                            weighted-average</strong> is the quantity-weighted
                            price of the standard scheduled activations;
                            <strong>direct weighted-average</strong> is the
                            corresponding price for direct activations.
                            <strong>Market price</strong> is the common current
                            scheduled product. <strong>Legacy marginal
                            price</strong> is the historical product and is
                            not spliced onto the current market price. These
                            differences describe distinct procurement or
                            activation processes, not alternative ways of
                            averaging the same observation.
                        </dd>


                        <dt>
                            <strong>
                                RR — Replacement Reserve
                            </strong>
                        </dt>

                        <dd style="margin: 3px 0 12px 20px;">
                            RR is the reserve-replacement layer: it restores
                            the reserve headroom used by faster services so
                            the system is ready for the next imbalance. The
                            activation price is the EUR/MWh price assigned to
                            the replacement-reserve energy activated in that
                            period. It is an energy price, not a capacity
                            availability price, and its direction still means
                            upward or downward net injection. The public RR
                            series is Portugal's REN product; its legacy hourly
                            and current 15-minute components remain separate.
                        </dd>


                        <dt>
                            <strong>
                                Balancing and imbalance settlement
                            </strong>
                        </dt>

                        <dd style="margin: 3px 0 0 20px;">
                            Balancing actions are the system operator's
                            real-time corrections. Imbalance settlement is the
                            later financial calculation that charges or credits
                            market participants whose actual position differs
                            from their scheduled position. A reserve price, an
                            activated-energy price and an imbalance-settlement
                            price therefore describe different variables.
                        </dd>

                    </dl>

                    <p>
                        <strong>What the selectors mean.</strong>
                        The labels below describe the exact variable returned by
                        the selected Spanish REE/ESIOS product; they are not
                        interchangeable measures of one balancing price.
                    </p>

                    <div style="overflow-x: auto;">
                        <table style="white-space: normal; min-width: 920px;">
                            <thead>
                                <tr>
                                    <th>Selector</th>
                                    <th>Plain-language meaning</th>
                                    <th>Unit</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr><td><strong>aFRR energy — marginal price</strong></td><td>Price of the marginal automatically activated upward or downward balancing-energy offer in the selected direction.</td><td>EUR/MWh</td></tr>
                                <tr><td><strong>aFRR capacity — marginal price</strong></td><td>Marginal price paid for holding a unit of aFRR capacity available, rather than for energy actually activated.</td><td>EUR/MW</td></tr>
                                <tr><td><strong>aFRR capacity — weighted-average price</strong></td><td>Capacity-market price averaged with the awarded capacity as weights for the selected direction.</td><td>EUR/MW</td></tr>
                                <tr><td><strong>mFRR scheduled — weighted-average price</strong></td><td>Weighted-average price of manually activated balancing energy scheduled through the standard scheduled process.</td><td>EUR/MWh</td></tr>
                                <tr><td><strong>mFRR scheduled — market price</strong></td><td>The common scheduled mFRR market price published for the period; it is a separate current product, not a continuation of the legacy series.</td><td>EUR/MWh</td></tr>
                                <tr><td><strong>mFRR direct — weighted-average price</strong></td><td>Weighted-average price of manually activated energy dispatched directly, outside the scheduled activation product.</td><td>EUR/MWh</td></tr>
                                <tr><td><strong>mFRR scheduled — legacy marginal price</strong></td><td>Historical marginal price of the former scheduled tertiary-regulation product. It is kept separate from current mFRR market prices.</td><td>EUR/MWh</td></tr>
                            </tbody>
                        </table>
                    </div>

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
                    Sources: OMIE and Red Eléctrica de España — ESIOS.
                    ESIOS indicator IDs are retained in the downloadable data.
                    Market-time calculations use Europe/Madrid. REE/ESIOS use
                    and publication follow the
                    <a href="https://www.ree.es/es/aviso-legal"
                       target="_blank" rel="noopener">REE Legal Notice</a>.
                </p>

            </div>

        </details>


        <details style="margin-top: 18px;">

            <summary>
                Market evolution storyline
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
                    This chronology separates a market launch or redesign from
                    the first date contained in this public database. A
                    coverage start does not necessarily mean that the market
                    itself began on that date. Matching events are also drawn
                    as dashed vertical markers on the chart for the selected
                    series and date range.
                </p>


                <div style="border-left: 3px solid #7f56d9; padding-left: 18px;">

                    <p>
                        <strong>1 Jan 1998 — Spanish day-ahead history begins.</strong><br>
                        OMIE's official historical workbook begins with hourly
                        Spanish day-ahead prices on this date. Portuguese
                        day-ahead prices begin on 1 July 2007, when Portugal
                        joined the Iberian market.
                    </p>

                    <p>
                        <strong>13 Jun 2018 — continuous intraday trading starts.</strong><br>
                        Spain and Portugal join the European continuous
                        intraday market. Continuous trades are summarized by
                        delivery period using OMIE's volume-weighted average
                        price.
                    </p>

                    <p>
                        <strong>24 May 2022 — current mFRR weighted-price history begins.</strong><br>
                        Upward and downward scheduled mFRR weighted-average
                        prices begin in the validated ESIOS series. Direct
                        upward activation begins on the same date; the direct
                        downward series begins on 15 Aug 2022.
                    </p>

                    <p>
                        <strong>14 Jun 2024 — intraday auctions are redesigned.</strong><br>
                        The former regional session structure gives way to
                        three pan-European intraday auctions. Old and new
                        sessions remain separate rather than being merged into
                        one synthetic history.
                    </p>

                    <p>
                        <strong>20 Nov 2024 — upward aFRR capacity marginal series begins.</strong><br>
                        This explains why selecting upward capacity marginal
                        prices before this date returns no observations even
                        though the downward series reaches back to 2018.
                    </p>

                    <p>
                        <strong>10 Dec 2024 — mFRR scheduled-price transition.</strong><br>
                        The legacy upward and downward marginal-price series
                        end. The current scheduled market-price series begins
                        as a distinct ESIOS product and is not spliced onto the
                        legacy values.
                    </p>

                    <p>
                        <strong>19 Mar 2025 — 15-minute intraday products.</strong><br>
                        Intraday auctions and continuous intraday trading add
                        quarter-hour products. Earlier hourly observations can
                        still be repeated for a 15-minute display, where they
                        are explicitly marked as upsampled.
                    </p>

                    <p style="margin-bottom: 0;">
                        <strong>1 Oct 2025 — 15-minute day-ahead market.</strong><br>
                        Day-ahead prices change from hourly to quarter-hourly
                        native resolution. Coarser displays continue to use
                        time-weighted means across the official periods.
                    </p>

                </div>

            </div>

        </details>


        <details style="margin-top: 18px;">

            <summary>
                Data coverage &amp; quality
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
                    Coverage below describes the current public database
                    release. The selector above the chart reads
                    the exact first and last dates for the chosen country,
                    product and auction session from the database catalog.
                </p>


                <div style="overflow-x: auto;">

                    <table
                        style="
                            white-space: normal;
                            min-width: 860px;
                        "
                    >

                        <thead>

                            <tr>
                                <th>Public product</th>
                                <th>Current coverage</th>
                                <th>Native resolution</th>
                                <th>Important interpretation</th>
                            </tr>


                        </thead>


                        <tbody>

                            <tr>

                                <td>
                                    <strong>Day-ahead</strong><br>
                                    Spain
                                </td>

                                <td>
                                    1 Jan 1998–20 Aug 2026
                                </td>

                                <td>
                                    Hourly before 1 Oct 2025;<br>
                                    15-minute from 1 Oct 2025
                                </td>

                                <td>
                                    OMIE-supplied hourly history is joined to
                                    the regularly collected series without
                                    changing official values.
                                </td>

                            </tr>

                            <tr>

                                <td>
                                    <strong>Day-ahead</strong><br>
                                    Portugal
                                </td>

                                <td>
                                    1 Jul 2007–20 Aug 2026
                                </td>

                                <td>
                                    Hourly before 1 Oct 2025;<br>
                                    15-minute from 1 Oct 2025
                                </td>

                                <td>
                                    Portuguese coverage starts with the
                                    official OMIE history supplied for the
                                    Portuguese bidding zone.
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <strong>Intraday auctions</strong><br>
                                    Spain and Portugal
                                </td>

                                <td>
                                    Historical sessions mainly begin on
                                    1 Jan 2018. Session 1 includes a
                                    31 Dec 2017 delivery-horizon record.
                                    End dates differ by session.
                                </td>

                                <td>
                                    Hourly historically;<br>
                                    15-minute products from 19 Mar 2025
                                </td>

                                <td>
                                    Sessions 1–6 are separate in the regional
                                    model. Three pan-European IDAs replace that
                                    structure from 14 Jun 2024. Sessions are
                                    never averaged into one synthetic price.
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <strong>Continuous intraday</strong><br>
                                    Spain and Portugal
                                </td>

                                <td>
                                    13 Jun 2018–19 Aug 2026
                                </td>

                                <td>
                                    Hourly historically;<br>
                                    15-minute products from 19 Mar 2025
                                </td>

                                <td>
                                    13 Jun 2018 is the market start, not a
                                    missing-data boundary. A known source gap
                                    remains on 29 Apr 2025.
                                </td>

                            </tr>


                            <tr>

                                <td>
                                    <strong>Balancing prices</strong><br>
                                    REE/ESIOS Spain
                                </td>

                                <td>
                                    aFRR energy: 1 Jan 2018–20 Aug 2026;<br>
                                    mFRR products: 1 Jan 2018–20 Aug 2026.
                                    Product-specific dates are shown by the
                                    live availability catalog.
                                </td>

                                <td>
                                    Hourly and 15-minute native observations
                                    are preserved per official indicator.
                                    Display frequencies use the
                                    methodology above.
                                </td>

                                <td>
                                    Capacity prices use EUR/MW; activated or
                                    scheduled energy prices use EUR/MWh.
                                    Upward and downward products, scheduled and
                                    direct activation, and legacy and current
                                    products remain distinct. Spanish RR will
                                    appear only after its historical data have
                                    been fully ingested and validated.
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
                    How publication quality is protected
                </h3>


                <ul style="margin-bottom: 0; padding-left: 20px;">
                    <li>
                        Raw/native source values and resolutions are preserved.
                    </li>
                    <li>
                        Period sequences, duplicates, nulls and daylight-saving
                        day lengths are validated during processing.
                    </li>
                    <li>
                        Missing official observations remain missing—never zero,
                        interpolated or replaced with another product.
                    </li>
                    <li>
                        Countries, auction sessions and economically different
                        price metrics remain distinct.
                    </li>
                    <li>
                        The deployment database is checked for SQLite integrity,
                        allowed tables, OMIE-only wholesale rows and
                        approved REE/ESIOS Spanish aFRR/mFRR rows only.
                    </li>
                    <li>
                        Market-design and resolution changes are stored as
                        dated events and displayed on relevant charts.
                    </li>
                </ul>


                <p
                    style="
                        margin: 16px 0 0;
                        color: #667085;
                        font-size: 12px;
                    "
                >
                    Current public release last includes official observations
                    through 20 August 2026. Product-specific end dates can be
                    earlier and are shown by the live availability catalog.
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
        "Public OMIE and REE/ESIOS electricity-market prices "
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

            This version exposes historical OMIE wholesale prices for Spain
            and Portugal, authorized REE/ESIOS aFRR and mFRR price series for
            Spain, plus ENTSO-E generation and installed-capacity fundamentals
            for Spain and Portugal. Each price product retains its official
            unit, direction, source identifier and native resolution.

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
</main>
"""

    if marker not in html:

        raise RuntimeError(
            (
                "Could not find page end "
                "for guide insertion."
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
        'id: "rr_activation_pt"',
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
        'id: "afrr_energy_marginal"',
        'id: "afrr_capacity_marginal"',
        'id: "afrr_capacity_weighted"',
        'id: "mfrr_scheduled_weighted_es"',
        'id: "mfrr_scheduled_market_es"',
        'id: "mfrr_direct_weighted_es"',
        'id: "mfrr_legacy_es"',
        "Public portfolio demo.",
        "Price series &amp; frequency methodology",
        "household electricity tariff",
        "FCR — Frequency Containment Reserve",
        "aFRR — automatic Frequency Restoration Reserve",
        "mFRR — manual Frequency Restoration Reserve",
        "RR — Replacement Reserve",
        "Balancing and imbalance settlement",
        "Start at earliest available",
        "Selected the earliest official data",
        "Data coverage &amp; quality",
        "Market evolution storyline",
        "20 Nov 2024 — upward aFRR capacity marginal series begins.",
        "10 Dec 2024 — mFRR scheduled-price transition.",
        "How publication quality is protected",
        "OMIE-supplied hourly history",
        "known source gap",
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

    if positions != sorted(positions):

        raise RuntimeError(
            (
                "Generated public dashboard has an invalid "
                f"section order: {ordered_sections}"
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

    print("  - Spanish REE/ESIOS aFRR")
    print("  - Spanish REE/ESIOS mFRR")

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
        "Balancing-market selectors: Spanish REE/ESIOS aFRR and mFRR"
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
