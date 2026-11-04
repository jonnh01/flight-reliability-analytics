# One-word commands for the whole pipeline. Run `make help` to list them.
# Uses the Python in your active virtual environment (.venv).

# Load .env so dbt and psql see the same database settings as the Python code
ifneq (,$(wildcard .env))
include .env
export
endif

DBT = cd dbt && dbt
PY  = python

.PHONY: help reset-db setup sample-data ingest ingest-offline dbt-build freshness export all test lint benchmark sensitivity app docs clean

help:            ## list commands
	@grep -E '^[a-z-]+:.*##' Makefile | awk -F':.*## ' '{printf "  make %-15s %s\n", $$1, $$2}'

setup:           ## install Python packages into the active virtual environment
	pip install -r requirements.txt

sample-data:     ## create 3 months of SYNTHETIC test files in data/landing (no internet needed)
	$(PY) scripts/make_sample_data.py --start 2026-05 --end 2026-07 --rows 20000

ingest:          ## download + load the rolling window (MONTHS_BACK in .env)
	$(PY) -m pipeline.ingest

ingest-offline:  ## load from data/landing or the archive only (never calls BTS)
	$(PY) -m pipeline.ingest --offline --latest 2026-07 --months-back 3

dbt-build:       ## build all models and run all tests (stops on any failing test)
	$(DBT) build --profiles-dir .

freshness:       ## warn if the newest loaded month is too old
	$(DBT) source freshness --profiles-dir .

export:          ## write data/marts/*.parquet for the app (+ CSVs for Tableau)
	$(PY) -m pipeline.export

all: ingest dbt-build export   ## the full monthly refresh, in order

test:            ## Python unit tests (+ database tests when Postgres is reachable)
	$(PY) -m pytest -q

lint:            ## style and error checks
	ruff check .

benchmark:       ## EXPLAIN ANALYZE before/after indexes -> docs/benchmarks.md
	$(PY) analysis/benchmarks/run_benchmarks.py --runs 5

sensitivity:     ## scorecard robustness check -> docs/scorecard_sensitivity.md
	$(PY) analysis/scorecard_sensitivity.py

app:             ## open the dashboard at http://localhost:8501
	streamlit run app/streamlit_app.py

docs:            ## open dbt's documentation site with the lineage graph
	$(DBT) docs generate --profiles-dir . && $(DBT) docs serve --profiles-dir .

reset-db:        ## DELETE all loaded data and dbt tables in Postgres (e.g. after testing with synthetic data)
	psql -d $${PGDATABASE:-flights} -c "drop schema if exists raw, staging, intermediate, marts, reference cascade;"

clean:           ## delete local caches (keeps data/archive and data/marts)
	rm -rf data/cache dbt/target dbt/logs .pytest_cache
