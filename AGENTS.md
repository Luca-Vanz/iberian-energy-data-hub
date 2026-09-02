# AGENTS.md

## Project

This repository is the **Iberian Energy Data Hub**, a Python portfolio project for historical electricity-market data and analytics for Spain and Portugal.

The project is intended to be:
- technically solid;
- useful as a public portfolio project;
- understandable enough that the owner can explain the architecture and implementation in job interviews;
- conservative with data quality: do not invent, interpolate, or silently repair missing official data.

Repository:
- GitHub: `https://github.com/Luca-Vanz/iberian-energy-data-hub`
- Production: `https://iberian-energy-data-hub.onrender.com/`

Main stack:
- Python
- pandas
- requests
- SQLite
- SQL
- FastAPI
- Chart.js
- VS Code
- Git / GitHub
- Render

---

## Working style

The project owner wants to understand what is happening, not just receive opaque code.

When making changes:
1. Inspect the existing implementation first.
2. Explain the change in practical terms.
3. Prefer minimal, coherent changes over unnecessary rewrites.
4. Run the relevant automated tests.
5. Report exactly what changed and whether tests passed.
6. Do not fabricate data or silently fill official-source gaps.
7. Preserve raw/native data and make display transformations explicit.

When suggesting terminal commands, prefer commands that are safe on Windows PowerShell where relevant.

---

## Git workflow

Branches:
- `main` = stable public production branch used by Render.
- `develop` = ongoing development branch.

Important:
- **Never use `git add .`** in this repository.
- There are often unrelated local uncommitted pipeline files.
- Stage only the exact files intended for the current change.
- Do not discard or overwrite unrelated user work.
- Render Auto-Deploy is intentionally OFF.
- Production deploys are manual after testing.

Before any production deployment:
1. Test on `develop`.
2. Push `develop`.
3. Update `main` only after validation.
4. Trigger a manual Render deploy.
5. Verify the live site.

---

## Public vs local data

The local research database contains:
- OMIE wholesale data;
- ESIOS balancing data;
- REN balancing data.

The public production database may contain:
- OMIE wholesale data;
- validated Spanish REE/ESIOS aFRR and mFRR price series;
- validated Spanish REE/ESIOS RR price series once its historical ingestion is complete.

Publicly allowed markets:
- `day_ahead`
- `intraday_auction`
- `intraday_continuous`

Publicly forbidden:
- incomplete or unvalidated Spanish RR history;
- Portuguese RR and all other REN balancing data until separately authorized;
- any ESIOS product outside the explicitly validated Spanish aFRR, mFRR, and RR price series.

The public API may serve the approved Spanish ESIOS series above. It must reject
unapproved country/source/product combinations with HTTP 403 and must never
silently substitute Portuguese RR for Spanish RR.

Never expose, print, commit, or embed any private ESIOS token or other credentials.

---

## Application modes

The application supports public and local modes through environment configuration.

Production Render environment:
```text
IBERIAN_APP_MODE=public
```

The public app uses the sanitized public SQLite database.

The public dashboard is `src/web/public_index.html`.

The full/local dashboard is `src/web/index.html`.

The public dashboard may present only ancillary selectors backed by approved,
validated Spanish ESIOS data. Do not present Portuguese RR or an empty Spanish
RR selector.

Use a separate browser cache key for the public market catalog.

---

## Public deployment architecture

The public SQLite database is too large to keep in normal Git history.

Current public DB build:
- decompressed size: about 975.02 MB;
- compressed gzip size: about 86.92 MB;
- OMIE unified rows: 1,522,979;
- approved Spanish ESIOS aFRR/mFRR rows: 1,446,763.

The compressed DB is distributed as a GitHub Release asset:
```text
iberian_energy_public.db.gz
```

Publish each rebuilt database as a new GitHub Release asset; production's
`PUBLIC_DB_URL` must point to that exact validated release.

Render build command:
```bash
pip install -r requirements.txt && python -m src.database.fetch_public_database
```

Render start command:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

Render environment:
```text
IBERIAN_APP_MODE=public
PUBLIC_DB_URL=https://github.com/Luca-Vanz/iberian-energy-data-hub/releases/download/<validated-release-tag>/iberian_energy_public.db.gz
```

Health check:
```text
/health
```

Do not rebuild or re-upload the public DB for frontend-only changes.

---

## Public database builder

`src/database/build_public_database.py`

Purpose:
- build `deployment/iberian_energy_public.db`;
- include OMIE wholesale data and approved Spanish ESIOS aFRR/mFRR data;
- preserve legacy day-ahead compatibility;
- copy wholesale market events;
- create public catalog cache;
- validate the database before use.

Expected public tables:
```text
market_catalog_cache
market_events
market_price_data
omie_day_ahead_prices
balancing_market_data
```

Expected public-data rules:
- unified wholesale source must be OMIE only;
- balancing rows must be Spanish ESIOS aFRR/mFRR only;
- no REN rows;
- SQLite integrity must pass.

`deployment/iberian_energy_public.db` and its `.gz` file are generated deployment artifacts and must remain ignored by Git.

---

## Public database fetcher

`src/database/fetch_public_database.py`

Purpose:
- download the GitHub Release gzip asset;
- decompress to a temporary SQLite file;
- validate it;
- atomically replace the deployed public DB.

Validation includes:
- SQLite quick/integrity check;
- exact expected tables;
- OMIE-only unified wholesale sources;
- Spanish ESIOS aFRR/mFRR-only balancing rows;
- allowed wholesale-market set;
- market catalog availability.

Do not weaken these validation checks without a clear reason.

---

## Unified market-price schema

Core table:

```sql
CREATE TABLE market_price_data (
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
 PRIMARY KEY(
   timestamp_utc,
   country,
   market,
   market_stage,
   direction,
   session,
   source_id
 )
);
```

Important semantics:
- preserve `native_resolution_minutes`;
- preserve auction sessions;
- preserve source identifiers;
- do not merge distinct market products;
- do not compare or aggregate incompatible units.

---

## Dashboard contract

The dashboard uses one main price graph.

Core selectors:
- display frequency;
- price type;
- Spain / Portugal / both;
- date range;
- direction where relevant;
- auction session where relevant.

Supported display frequencies:
- 15 min
- 1 h
- daily
- weekly
- monthly
- yearly

Backend performs resampling.

Frontend must not invent values.

Market changes are represented through `market_events`, not hard-coded into chart logic where avoidable.

Intraday auctions and continuous intraday are distinct products.

Auction sessions must remain distinct.

---

## Frequency methodology

The public dashboard should explain this clearly.

### Native and upsampled display

If requested display resolution is finer than native source resolution:
- repeat the native official value across the finer display periods;
- do not interpolate;
- clearly mark the result as upsampled;
- dashed chart styling is appropriate for repeated/upsampled sections.

Example:
- one official hourly price displayed at 15-minute frequency becomes four repeated 15-minute display points;
- this is a visualization transformation, not four new official prices.

### Coarser aggregation

When displaying at a coarser frequency:
- use a time-weighted mean based on each observation's native duration.

This prevents 15-minute periods from receiving disproportionate weight relative to 60-minute periods in mixed-resolution history.

### Calendar boundaries

Use MIBEL market time:
```text
Europe/Madrid
```

Weekly aggregation:
- Monday through Sunday.

### Missing data

Missing official observations remain missing.
Do not:
- replace them with zero;
- interpolate across source gaps;
- invent substitute prices.

---

## Public price-series definitions

The public legend/methodology guide should explain:

### Day-ahead price
OMIE day-ahead market-clearing price for each electricity delivery period and bidding zone.

Unit:
```text
EUR/MWh
```

### Intraday auction price
OMIE clearing price for the selected intraday auction session and delivery period.

Important:
- sessions are separate;
- do not combine sessions into one synthetic series.

Unit:
```text
EUR/MWh
```

### Continuous intraday weighted-average price
Volume-weighted average price of continuous intraday trades for each electricity delivery period.

Unit:
```text
EUR/MWh
```

---

## Known data status

### OMIE day-ahead

Historical coverage:
```text
2018-01-01 to 2026-08-20
```

Validated dates:
```text
3154
```

Native resolution:
- before 2025-10-01: hourly;
- from 2025-10-01: 15-minute.

Unified rows:
```text
198,046
```

Spain and Portugal:
```text
99,023 each
```

### OMIE intraday auctions

Unified rows:
```text
839,506
```

Spain:
```text
419,753
```

Portugal:
```text
419,753
```

Historical sessions:
```text
1–6
```

Modern sessions:
```text
1–3
```

Known official/source gaps exist.

Examples:
- 2026-08-04 session 1;
- 2026-08-05 session 1.

Those raw files were effectively empty and correctly produce zero database rows.

Do not fabricate replacements.

### OMIE continuous intraday

Historical coverage:
```text
2018-06-13 to 2026-08-19
```

Unified rows:
```text
218,018
```

Spain:
```text
109,009
```

Portugal:
```text
109,009
```

Known source gap:
```text
2025-04-29
```

Do not fill it.

---

## Market events

Current wholesale events cover Spain and Portugal separately:

- 2018-06-13: continuous intraday start;
- 2024-06-14: intraday auction redesign;
- 2025-03-19: intraday auction 15-minute resolution;
- 2025-03-19: continuous intraday 15-minute resolution;
- 2025-10-01: day-ahead 15-minute resolution.

Public market events currently total:
```text
10
```

Balancing events are not part of the public deployment.

---

## API

Core endpoint:
```text
GET /market/prices
```

Typical parameters:
```text
market
country
direction
start_date
end_date
frequency
session
```

Catalog:
```text
GET /market/catalog
```

Health:
```text
GET /health
```

About:
```text
GET /about
```

Public mode requirements:
- `/health` reports `mode: public`;
- public catalog contains wholesale plus approved Spanish aFRR/mFRR;
- Portuguese balancing and RR requests return HTTP 403.

---

## Automated tests

Main market API regression suite:
```powershell
python tests\smoke_test_market_api.py
```

Last known result:
```text
Passed: 16
Failed: 0
Warnings: 0
```

Public-mode smoke test:
```powershell
python tests\smoke_test_public_mode.py
```

Last known result:
```text
Passed: 11
Failed: 0
Warnings: 0
```

Prefer automated tests over repeated manual browser testing.

---

## Catalog performance

`/market/catalog` used to rebuild from millions of rows and took roughly 55 seconds.

This was fixed using:
```text
src/database/build_market_catalog_cache.py
```

and a cached API lookup.

Current catalog response is roughly near-instant.

Do not reintroduce full-table catalog reconstruction on normal API requests.

---

## Public dashboard generation

The public dashboard is generated from the full dashboard through:
```text
src/web/build_public_dashboard.py
```

Purpose:
- inherit the stable dashboard UI;
- retain approved Spanish aFRR/mFRR selectors and remove RR/REN selectors;
- apply a separate public cache key;
- add public-specific explanatory content.

After changing this generator, regenerate:
```powershell
python -m src.web.build_public_dashboard
```

Then rerun:
```powershell
python tests\smoke_test_public_mode.py
```

---

## Current milestone

Production is live and validated at:
```text
https://iberian-energy-data-hub.onrender.com/
```

Current production state:
- OMIE wholesale plus Spanish ESIOS aFRR/mFRR public dashboard;
- sanitized public DB;
- GitHub Release DB distribution;
- Render build downloads/decompresses/validates the DB;
- RR, REN and unapproved balancing data blocked publicly;
- health checks passing.

---

## Current next task

Improve recruiter-facing presentation of the public site.

Immediate requested feature:
**add a clear legend / methodology section explaining each public price series and how every display frequency is calculated.**

The section should explain:
- Day-ahead price;
- Intraday auction price;
- Continuous intraday weighted-average price;
- 15-minute display behavior;
- hourly aggregation;
- daily aggregation;
- weekly aggregation;
- monthly aggregation;
- yearly aggregation;
- time-weighted means;
- native vs display resolution;
- dashed styling for upsampled data;
- missing-data policy;
- MIBEL market-time calendar logic.

Before implementing:
1. inspect `src/analytics/unified_prices.py`;
2. inspect `src/web/index.html`;
3. inspect `src/web/build_public_dashboard.py`;
4. ensure all methodology text matches actual backend behavior.

After implementing:
1. regenerate `public_index.html`;
2. run the public smoke test;
3. report changed files;
4. do not touch unrelated pipeline files;
5. do not deploy automatically unless explicitly asked.

---

## Longer-term roadmap

Likely next areas after public presentation:
- better About / methodology page;
- recruiter-facing project explanation;
- demand / generation fundamentals;
- more market analytics;
- econometric analysis;
- day-ahead electricity price forecasting;
- machine-learning experiments;
- portfolio-ready documentation.

Prefer completing one coherent feature at a time rather than expanding scope unnecessarily.
