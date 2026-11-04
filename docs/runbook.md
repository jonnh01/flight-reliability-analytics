# Runbook: monitoring and fixing the pipeline

## Where to look

| Signal | Where |
|---|---|
| Did the monthly run work? | GitHub → Actions → *Monthly refresh* (green tick / red X). The run page has a summary of months loaded |
| Failure alert | A GitHub issue titled "Monthly refresh failed" is opened automatically (you get an email) |
| Detailed logs | Run page → *Artifacts* → `pipeline-logs-…` (`logs/pipeline.log`, `logs/last_run.json`, dbt `run_results.json`) |
| Local run history | `select * from raw.pipeline_runs order by started_at desc;` |
| What is loaded | `select * from raw.load_log order by year_month;` |
| Data freshness | Dashboard sidebar, or `dbt source freshness --profiles-dir .` |

## Common failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `MonthNotPublished` for every recent month | BTS changed the download URL, or blocks your network | Open the URL from `pipeline/bts.py` in a browser. If the site works manually, download the ZIP and put it in `data/landing/` (name must end `_YEAR_MONTH.zip`, e.g. `_2026_7.zip`), then rerun. Update `BTS_URL_TEMPLATE` if the pattern changed |
| `SSLError` / certificate errors on download | BTS certificate chain problem on your machine | `pip install --upgrade certifi`; if it persists, use the manual `data/landing/` route. Never disable SSL verification |
| `SourceSchemaError: missing required column(s)` | BTS renamed or removed a column | Compare the file header to `COLUMN_MAP` in `pipeline/bts.py`, map the new name, document it in `docs/decisions.md` |
| `file has N rows but M were loaded` | COPY was interrupted or CSV quoting problem | Rerun the month with `--month YYYY-MM --force`. The transaction rolled back, so the old data is still intact |
| dbt test `assert_fct_reconciles_with_raw` fails | Fact table out of sync with raw (e.g. a load ran but dbt did not) | `cd dbt && dbt build --profiles-dir . --full-refresh` |
| dbt `unique` test on `fct_flights.flight_id` fails | Two source rows share date, carrier, flight number, route and scheduled time | Query the duplicates (`select flight_id, count(*) from marts.fct_flights group by 1 having count(*) > 1`), inspect them in raw, decide a rule, document it |
| `assert_no_month_missing_from_window` fails | A month in the middle failed to load | Load it: `python -m pipeline.ingest --month YYYY-MM` |
| Source freshness error | Newest month is over 6 months old: the refresh has stopped working | Check the last few Actions runs |
| Actions run out of disk / time | 24 months is too big for the free runner | Set repository variable `MONTHS_BACK` to 12 |
| Streamlit app shows old data | Monthly job failed before publishing (by design), or Streamlit did not redeploy | Check Actions; in Streamlit Cloud, *Reboot app* |

## Useful commands

```bash
python -m pipeline.ingest --month 2026-07 --force   # reload one month
python -m pipeline.ingest --months-back 24          # backfill
python -m pipeline.ingest --offline                 # no BTS access: landing/archive only
cd dbt && dbt build --profiles-dir . --full-refresh # rebuild every model from scratch
cd dbt && dbt test --profiles-dir . --select fct_flights   # re-run one model's tests
```

## Testing failure handling on purpose (Phase 5 checks)

1. **Bad file:** put a ZIP containing a CSV with a missing column in `data/landing/`, run `--month` for it → expect `SourceSchemaError`, a `failed` row in `raw.pipeline_runs`, and the old data untouched.
2. **Interrupted load:** start a large load and press Ctrl+C during COPY → rerun; counts must reconcile.
3. **Failing test blocks publishing:** temporarily set `has_min_rows: {min_rows: 999999999}` on a mart, run `make all` → `dbt build` fails and `pipeline.export` never runs. Revert afterwards.
4. **Rerun is harmless:** run `python -m pipeline.ingest` twice → the second run reports `no_new_data`.
