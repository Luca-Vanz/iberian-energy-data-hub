# Iberian Energy Data Hub

A data-engineering and analytics project for exploring the Spanish and
Portuguese electricity markets with official market data.

The project collects, standardises, validates and stores electricity-market
observations in SQLite, exposes them through FastAPI, and presents them in an
interactive web dashboard.

## Live demo

[Open the Iberian Energy Data Hub](https://iberian-energy-data-hub.onrender.com/)

The public deployment contains sanitized **OMIE wholesale prices** and
authorized **Spanish REE/ESIOS aFRR and mFRR price series**.
Balancing-market and REN fundamental datasets remain in the local research
environment and are not redistributed publicly while reuse permissions are
being clarified.

## Public dashboard

The live dashboard currently provides:

- Day-ahead prices for Spain and Portugal
- Intraday-auction prices with sessions kept separate
- Continuous-intraday weighted-average prices
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

The chart intentionally limits very large high-resolution selections for
browser usability. CSV downloads can use any supported frequency across the
complete selected availability range and are retrieved in calendar-aligned,
bounded chunks when
necessary.

## Current public coverage

| Product | Coverage in the current public database | Native resolution |
| --- | --- | --- |
| Day-ahead, ES and PT | 1 Jan 2018–20 Aug 2026 | Hourly before 1 Oct 2025; 15-minute from 1 Oct 2025 |
| Intraday auctions, ES and PT | Mainly from 1 Jan 2018; session 1 includes a 31 Dec 2017 delivery-horizon record; end dates vary by session | Historically hourly; 15-minute products from 19 Mar 2025 |
| Continuous intraday, ES and PT | 13 Jun 2018–19 Aug 2026 | Historically hourly; 15-minute products from 19 Mar 2025 |

Important interpretation notes:

- Intraday-auction sessions are never averaged into a synthetic price.
- Three pan-European intraday auctions replaced the six-session regional
  structure from 14 Jun 2024.
- Continuous intraday starts on 13 Jun 2018 because that is the market start.
- A known continuous-intraday source gap remains on 29 Apr 2025.
- Earlier official day-ahead and auction files have been requested from OMIE;
  unavailable observations are not inferred or interpolated.

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
| `public` | `deployment/iberian_energy_public.db` by default | OMIE wholesale prices plus authorized Spanish REE/ESIOS aFRR and mFRR prices; other balancing sources remain blocked |
| `local` | `data/database/iberian_energy.db` by default | Full research environment, including locally held fundamentals and balancing-market work |

An alternative database path can be supplied with `IBERIAN_DB_PATH`.

## API

The unified endpoints are:

- `GET /market/catalog` — available markets, countries, products, resolutions
  and date coverage
- `GET /market/prices` — unified price-series query
- `GET /health` — application mode and service status
- `GET /about` — deployment scope and source summary
- `GET /docs` — interactive FastAPI documentation

Example:

```text
/market/prices?market=day_ahead&country=both&start_date=2026-08-01&end_date=2026-08-03&frequency=1h
```

Supported frequencies are `15min`, `1h`, `daily`, `weekly`, `monthly` and
`yearly`. Intraday-auction queries can also specify `session=1` through
`session=6` where those sessions exist.

Legacy OMIE endpoints remain available for backward compatibility.

## Architecture

```text
Official sources (OMIE / REE-ESIOS / local research sources)
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
REE/ESIOS aFRR and mFRR prices. REN and every other balancing source remain
excluded. The database is compressed as a deployment artifact and fetched
during the Render build, which verifies SQLite integrity, allowed tables,
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
not shown because no validated FCR price series is present locally; RR and REN
data remain outside the public release.
