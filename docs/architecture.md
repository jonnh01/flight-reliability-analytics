# Architecture

## Data flow

| Step | What happens | Code |
|---|---|---|
| 1. Source | BTS publishes one ZIP per month (~500-600k flights), about 2 months after the month ends | — |
| 2. Ingest | Find the newest published month; for each month in the rolling window: get the ZIP (local cache → `data/landing` → raw archive → BTS download with retries), check it is a real ZIP with the required columns | `pipeline/ingest.py`, `pipeline/bts.py` |
| 3. Archive | Store the untouched ZIP with its SHA-256 checksum: S3 (`S3_BUCKET` set) or `data/archive/` | `pipeline/storage.py` |
| 4. Load | If the checksum matches what is already loaded, skip. Otherwise delete the month and COPY it in again, in one transaction, then reconcile row counts. Months outside the window are pruned | `pipeline/db.py` |
| 5. Transform | dbt: staging (types, parsing) → intermediate (business rules, aircraft rotation with LAG) → marts (star schema + reporting tables) | `dbt/models/` |
| 6. Validate | 50+ dbt tests run inside `dbt build`; a failing test stops the build | `dbt/models/**/_*.yml`, `dbt/tests/` |
| 7. Analyse | Statistics notebook, scorecard sensitivity, query benchmarks | `analysis/` |
| 8. Export | Marts → Parquet (app, committed) and CSV (Tableau); flight sample for the notebook | `pipeline/export.py` |
| 9. Publish | Streamlit Community Cloud redeploys when `data/marts/` changes on GitHub | `app/` |
| 10. Automate | CI on every push (synthetic data); monthly refresh on the 15th | `.github/workflows/` |

## Key design decisions

**Raw layer is all text.** The loader never rejects a row because of an unexpected value. Typing happens in dbt staging, where problems surface as failing tests instead of crashed loads.

**Idempotent loads.** Each month is replaced whole inside one transaction, keyed by `year_month`, and skipped when its checksum is unchanged. Rerunning never duplicates data, and a crash mid-load leaves the previous version intact.

**Revised source files.** If BTS republishes a month, its checksum changes, the loader reloads it, and the incremental fact table replaces that month (delete+insert on `year_month`).

**Incremental fact table.** `fct_flights` processes only rows with a newer `loaded_at` than it already holds. A post-hook removes months pruned from the window. `dbt build --full-refresh` rebuilds everything.

**Why S3?** GitHub Actions runners have no permanent disk or database. The raw archive lets each monthly run rebuild the rolling window without re-downloading two years from BTS, and keeps the exact source files for reprocessing or audit. Without S3, the Actions cache plays the same role (less durable: GitHub evicts caches unused for 7 days).

**Why Parquet for the app?** The public app needs no database server (free hosting, nothing to secure), and the files are small because they are already aggregated.

**Publishing guard.** The workflow order is ingest → `dbt build` → export → commit. Any failure stops the job before the commit, so the live app keeps showing the last good data, and an issue is opened.

## Environments

| | Local (Mac) | Docker | GitHub Actions |
|---|---|---|---|
| Postgres | Postgres.app on port 5432 | `db` service, port 5433 on the Mac | service container, thrown away after the run |
| Raw archive | `data/archive/` or S3 | same, mounted from the Mac | S3 or Actions cache |
| Trigger | you run `make all` | `docker compose run --rm pipeline` | 15th of each month, or "Run workflow" |

## Known limits

- GitHub runners have about 14 GB of free disk and 7 GB of RAM. 24 months (~13-14M rows) should fit, but check the first run's duration and disk use. Lower `MONTHS_BACK` (repository variable) if needed.
- If BTS blocks downloads from GitHub's servers, run `python -m pipeline.ingest` on your Mac with S3 turned on. The Actions run then restores every month from S3 and never needs to reach BTS.
