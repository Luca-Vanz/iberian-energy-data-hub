# Iberian Energy Data Hub

A data-engineering and analytics project for exploring the Spanish and
Portuguese electricity markets with official market data.

The project collects, standardises, validates and stores electricity-market
observations in SQLite, exposes them through FastAPI, and presents them in an
interactive web dashboard.

## Live demo

[Open the Iberian Energy Data Hub](https://iberian-energy-data-hub.onrender.com/)

[Download the current public database release](https://github.com/Luca-Vanz/iberian-energy-data-hub/releases/tag/public-db-2026-09-03-fundamentals)

The public deployment contains sanitized **OMIE wholesale prices** and
authorized **Spanish REE/ESIOS aFRR and mFRR price series**. Spanish RR will be
published only after its historical ingestion is complete and validated;
Portuguese REN balancing data remain in the local research environment.

## Public dashboard

The live dashboard currently provides:

- Day-ahead prices for Spain and Portugal
- Intraday-auction prices with sessions kept separate
- Continuous-intraday weighted-average prices
- Spanish REE/ESIOS aFRR energy and capacity prices
- Spanish REE/ESIOS scheduled and direct mFRR prices
- 15-minute, hourly, daily, weekly, monthly and yearly views
- Separate Spain, Portugal and combined-country selections
- Market-event and data-resolution context
- Selected-range CSV downloads independent of chart display limits, with the
  exact-value preview beside the download controls
- Product-specific no-data guidance showing available directions, native
  resolutions and date ranges
- A market-evolution storyline covering launches, redesigns and resolution
  changes
- A public price-series and frequency methodology
- A data-coverage and publication-quality guide
- Friendly progress feedback for larger graph requests
- Research graphs for installed capacity and monthly generation by technology
  in Spain and Portugal, using official ENTSO-E data

The chart intentionally limits very large high-resolution selections for
browser usability. CSV downloads can use any supported frequency across the
complete selected availability range and are retrieved in calendar-aligned,
bounded chunks when
necessary.

## Current public coverage

| Product | Coverage in the current public database | Native resolution |
| --- | --- | --- |
| Day-ahead, ES | 1 Jan 1998–20 Aug 2026 | Hourly before 1 Oct 2025; 15-minute from 1 Oct 2025 |
| Day-ahead, PT | 1 Jul 2007–20 Aug 2026 | Hourly before 1 Oct 2025; 15-minute from 1 Oct 2025 |
| Intraday auctions, ES and PT | Mainly from 1 Jan 2018; session 1 includes a 31 Dec 2017 delivery-horizon record; end dates vary by session | Historically hourly; 15-minute products from 19 Mar 2025 |
| Continuous intraday, ES and PT | 13 Jun 2018–19 Aug 2026 | Historically hourly; 15-minute products from 19 Mar 2025 |
| aFRR energy, ES | 1 Jan 2018–20 Aug 2026 | Hourly and 15-minute, depending on date and indicator |
| aFRR capacity, ES | Downward series from 1 Jan 2018; upward marginal series from 20 Nov 2024; through 20 Aug 2026 | Hourly and 15-minute, depending on date and indicator |
| mFRR scheduled, ES | Legacy marginal series from 1 Jan 2018–10 Dec 2024; current weighted-average series from 24 May 2022 and market-price series from 10 Dec 2024; through 20 Aug 2026 | Hourly legacy observations and 15-minute current products |
| mFRR direct, ES | Upward from 24 May 2022; downward from 15 Aug 2022; through 20 Aug 2026 | 15 minutes |
| Installed capacity, ES and PT | Annual observations, 2018–2026 | Annual |
| Generation by technology, ES and PT | Monthly energy totals, Jan 2018–Sep 2026 (current month partial) | Calculated from native hourly or 15-minute observations |

Important interpretation notes:

- Intraday-auction sessions are never averaged into a synthetic price.
- Three pan-European intraday auctions replaced the six-session regional
  structure from 14 Jun 2024.
- Continuous intraday starts on 13 Jun 2018 because that is the market start.
- A known continuous-intraday source gap remains on 29 Apr 2025.
- OMIE's supplied day-ahead workbook is integrated through 30 Sep 2025;
  unavailable observations are not inferred or interpolated.
- OMIE's supplied intraday-auction archive is being validated separately
  because its historical format differs from the modern daily files.
- aFRR capacity prices are measured in EUR/MW; balancing-energy prices are
  measured in EUR/MWh. These economically different variables remain separate.
- Upward means increasing net system energy; downward means reducing net
  system energy. Directions are never combined unless the user explicitly
  selects both for display.

Coverage is product-specific and will change as new validated official data is
added. The live catalog is the authoritative source for selectable dates.

## Frequency methodology

Source observations retain their native values and resolution. Display and
download frequencies are calculated as follows:

- **15 minutes:** native 15-minute observations are used directly; native
  hourly prices are repeated across their four quarter-hours and marked as
  upsampled.
- **Hourly:** a native hourly value is retained; four native quarter-hours are
  combined using a duration-weighted mean.
- **Daily:** duration-weighted mean of the available delivery periods in the
  Europe/Madrid calendar day.
- **Weekly:** duration-weighted mean for Monday–Sunday market weeks.
- **Monthly:** duration-weighted mean for each market-calendar month.
- **Yearly:** duration-weighted mean for each market-calendar year.

Missing official observations stay missing. Countries, auction sessions,
directions, stages and metrics are grouped separately.

## Public and local modes

The application has two explicit modes controlled by `IBERIAN_APP_MODE`:

| Mode | Database | Dashboard scope |
| --- | --- | --- |
| `public` | `deployment/iberian_energy_public.db` by default | OMIE wholesale prices and Spanish REE/ESIOS aFRR and mFRR prices; RR and Portuguese balancing series remain blocked |
| `local` | `data/database/iberian_energy.db` by default | Full research environment, including locally held fundamentals and balancing-market work |

An alternative database path can be supplied with `IBERIAN_DB_PATH`.

## API

The unified endpoints are:

- `GET /market/catalog` — available markets, countries, products, resolutions
  and date coverage
- `GET /market/prices` — unified price-series query
- `GET /health` — application mode and service status
- `GET /about` — deployment scope and source summary
- `GET /fundamentals/installed-capacity?country=ES` — annual capacity by technology
- `GET /fundamentals/generation?country=PT` — monthly generation and coverage by technology
- `GET /docs` — interactive FastAPI documentation

Example:

```text
/market/prices?market=day_ahead&country=both&start_date=2026-08-01&end_date=2026-08-03&frequency=1h
```

Supported frequencies are `15min`, `1h`, `daily`, `weekly`, `monthly` and
`yearly`. Intraday-auction queries can also specify `session=1` through
`session=6` where those sessions exist.

Legacy OMIE endpoints remain available for backward compatibility.

Public ancillary examples:

```text
/market/prices?market=afrr&country=ES&start_date=2026-08-03&end_date=2026-08-03&frequency=15min&direction=both&stage=energy&metric=marginal_price
/market/prices?market=mfrr&country=ES&start_date=2026-08-03&end_date=2026-08-03&frequency=15min&direction=both&stage=energy_scheduled&metric=weighted_average_price
```

## Architecture

```text
Official sources (OMIE / REE-ESIOS / ENTSO-E)
                         |
                         v
                 Python collectors
                         |
                         v
                  Raw source files
                         |
                         v
          Parsing, validation and QA checks
                         |
                         v
                 SQLite databases
                         |
                         v
       Unified analytics and resampling layer
                         |
                         v
                      FastAPI
                         |
                         v
              Interactive web dashboard
```

The public SQLite database is built separately. Its wholesale table is
validated as OMIE-only, while its balancing table is restricted to Spanish
REE/ESIOS aFRR and mFRR prices. Every other
balancing series remains excluded. The current build contains 1,522,979 OMIE
observations and 1,446,763 approved Spanish ESIOS observations across 13
ancillary catalogue series. It also contains 3,134 ENTSO-E monthly generation
rows and 361 ENTSO-E installed-capacity rows for Spain and Portugal. The
database is compressed as a deployment artifact and fetched during the Render
build, which verifies SQLite integrity, allowed tables,
markets, countries and sources before serving it.

## Data-quality principles

- Preserve official raw/native observations and resolutions
- Validate dates, periods, duplicates, nulls and daylight-saving transitions
- Keep missing data missing rather than silently repairing it
- Keep distinct products and dimensions separate
- Record material market-design and resolution changes
- Verify the sanitized public database before deployment
- Inspect future historical packages read-only before adding an importer

The public day-ahead database was independently compared with its downloaded
OMIE source files for the original quarter-hour validation period:

- 318 market days checked
- 30,528 quarter-hour periods
- 61,056 ES/PT prices compared
- 0 price mismatches
- 0 timestamp mismatches
- 0 missing or duplicate database rows

## Local setup

Create and activate a virtual environment, then install the pinned
dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run the local research application:

```powershell
$env:IBERIAN_APP_MODE = "local"
python -m uvicorn src.api.main:app --reload
```

Run against a prepared public database:

```powershell
$env:IBERIAN_APP_MODE = "public"
python -m uvicorn src.api.main:app --reload
```

Open `http://127.0.0.1:8000/` for the dashboard or
`http://127.0.0.1:8000/docs` for the API documentation.

## Validation and tests

Regenerate the public dashboard after changing the base dashboard or public
guide:

```powershell
python -m src.web.build_public_dashboard
```

Run the public-mode smoke test while the public application is available on
port 8001:

```powershell
$env:IBERIAN_APP_MODE = "public"
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8001
```

In a second terminal:

```powershell
python tests\smoke_test_public_mode.py
```

Additional checks include the unified market API smoke test, source/database
validators and the read-only OMIE historical-package inspector tests.

## Project status

The current public release combines OMIE wholesale-market prices with the
authorized Spanish REE/ESIOS aFRR and mFRR price series. Capacity prices
(EUR/MW) and energy prices (EUR/MWh), upward and downward directions, scheduled
and direct activation, and legacy and current products remain separate. FCR is
not shown because no validated FCR price series is present locally. Spanish RR
is also withheld until its full history is ingested and validated; REN and
other balancing datasets remain outside the public release.

Current production release:

- Application commit: `b351662`
- Database tag: `public-db-2026-09-02-ancillary`
- Decompressed database: approximately 975.02 MB
- Compressed release asset: approximately 86.92 MB
- Public-mode smoke test: 11 passed, 0 failed, 0 warnings
