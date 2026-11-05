# Flight Operations Reliability Analytics

**An automated pipeline over U.S. domestic flights (BTS on-time data) that scores airline and airport reliability, traces where delays come from, and publishes a live dashboard that refreshes monthly.**

## What it does

| Question | Where it is answered |
|---|---|
| How is on-time performance trending? Which airlines, airports and routes are best and worst? | App: *Executive overview*, *Airlines & airports* |
| What share of delay minutes comes from the airline, weather, air traffic control, security, or a late inbound aircraft? Do delays cascade? | App: *Delay causes & trends*; `mart_delay_propagation` |
| Which carrier-airport pairs are consistently unreliable once flight volume is accounted for? | App: *Reliability scorecard*; `mart_reliability_scorecard` |
| Are the differences real or noise? | `analysis/01_statistical_analysis.ipynb` (chi-square, Welch t-test, logistic regression, effect sizes) |

## Architecture

```
BTS monthly ZIP ──► Python ingest ──► raw archive (S3 or local) ──► Postgres raw tables
                    (download, retry,                                   │
                     validate, COPY,                                    ▼
                     idempotent)                         dbt: staging → intermediate → marts
                                                         (star schema, incremental fact,
                                                          60 data tests: stop on failure)
                                                                        │
                                                                        ▼
                                              Parquet / CSV extracts ──► Streamlit app, Tableau
GitHub Actions: CI on every push (synthetic data) + monthly refresh that publishes only if all tests pass
```

Details: [docs/architecture.md](docs/architecture.md)

## Tech stack

Python (pandas, requests, psycopg) · PostgreSQL · dbt Core · AWS S3 (optional) · Docker · GitHub Actions · scipy / statsmodels · Streamlit · Tableau Public

## Data model

Star schema, grain **one row per scheduled flight** (including cancelled and diverted flights).

- `fct_flights` (incremental, delete+insert by month) → `dim_date`, `dim_carrier`, `dim_airport`, `dim_route`
- Marts: `mart_carrier_monthly`, `mart_airport_monthly`, `mart_route_performance`, `mart_delay_causes`, `mart_delay_by_hour`, `mart_delay_propagation`, `mart_reliability_scorecard`, `mart_whatif_delayed_flights`, `mart_pipeline_status`

Definitions: [docs/metric_definitions.md](docs/metric_definitions.md) · Columns: [docs/data_dictionary.md](docs/data_dictionary.md)

## Data quality

dbt tests on every build: unique and not-null keys, fact-to-dimension relationships, accepted values, value ranges, **row-count reconciliation** (raw = fact = load log for every month), delay causes summing to arrival delay, no gaps in the month sequence, and source freshness. The monthly job publishes nothing if any test fails.

## Results on real data

Measured by the GitHub Actions runs on 2026-11-05 over 12 months of BTS data (Sep 2025 – Aug 2026). Nothing below is estimated.

| | |
|---|---|
| Flights loaded | **7,049,869** scheduled flights (515,037 to 631,970 per month), 14 carriers, 360 origin airports |
| Data tests | 60 dbt data tests on every build: 0 failures, 3 warnings (data-quality flags, below) |
| Run time on a GitHub runner | ingest 103–149 s from the raw-file cache (401 s on the first 12-month run, which downloaded the months not yet cached); `dbt build` 219–373 s |
| Monthly on-time rate (all scheduled flights) | 69.4% (Jul 2026) to 82.8% (Sep 2025) |
| Monthly cancellation rate | 0.51% (Sep 2025) to 4.71% (Jan 2026) |
| Dashboard | all 6 Streamlit page tests pass against these files in CI |

**Data-quality flags kept visible on purpose:** 1 completed flight with a blank arrival delay (counted as not on time, see [metric definitions](docs/metric_definitions.md)); 148 delayed flights whose five cause columns don't add up to the arrival delay; 2 flights with an arrival delay outside the expected range (−240 to 4,000 minutes). The carrier dimension also shows Hawaiian Airlines (HA) last reporting in Dec 2025 and Spirit (NK) in May 2026.

**Query performance** (indexes on `fct_flights`, 7,049,869 rows, median of 5 runs, identical results before and after; [details](docs/benchmarks.md)):

| Query | Without index | With index |
|---|---:|---:|
| One aircraft's flights on one day (`LAG` rotation) | 359.7 ms (full scan) | 0.007 ms (index scan) |
| One airport, latest 3 months, by carrier | 265.5 ms | 128.6 ms |
| One carrier's monthly trend | 278.8 ms | 188.2 ms |

Shared GitHub runners are noisy: an earlier run the same day measured 633.1 ms without the index for the aircraft query.

**Scorecard robustness** ([details](docs/scorecard_sensitivity.md)): 1,540 carrier-airport pairs ranked. Re-weighting keeps 6–8 of the top 10 and a Spearman rank correlation of 0.955–0.990 with the baseline. Removing the small-sample adjustment keeps only 4 of the top 10, which is why the adjustment is there.

## Run it yourself

```bash
cp .env.example .env              # fill in your Postgres user
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
createdb flights
python -m pipeline.ingest         # download + load MONTHS_BACK months
cd dbt && dbt build --profiles-dir . && cd ..
python -m pipeline.export
streamlit run app/streamlit_app.py
```

Or with Docker: `docker compose up -d db && docker compose run --rm pipeline && docker compose up app`

No internet access to BTS? `make sample-data` creates synthetic files and `make ingest-offline` loads them (the app then shows a "synthetic data" banner).

## Limitations

- BTS data covers large U.S. carriers' domestic flights only, published with a ~2-month lag; it is not real-time.
- Delay causes are reported by airlines and only for flights 15+ minutes late.
- Times are local clock times; overnight arrivals are inferred, and time-zone changes are not adjusted.
- The cascade analysis and regression show associations, not proven causes.
- The what-if page is a simplified hypothetical (no knock-on effects).

## Repository layout

```
pipeline/     ingestion (BTS download, S3/local archive, Postgres load) and export
dbt/          models (staging, intermediate, marts), tests, seeds, macros
analysis/     statistics notebook, scorecard sensitivity, query benchmarks
app/          Streamlit dashboard (5 pages)
scripts/      synthetic sample-data generator
tests/        pytest unit, database and app smoke tests
docs/         architecture, metric definitions, runbook, decisions, setup guides
.github/      CI and monthly refresh workflows
```
