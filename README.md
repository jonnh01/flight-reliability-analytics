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
                                                          50+ data tests: stop on failure)
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
