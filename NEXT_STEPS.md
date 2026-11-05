# Next steps: your manual checklist

The AI-assisted code is written. This file lists **what only you can do**, in order. Tick each box as you go. Times are rough.

## What has and hasn't been tested yet (updated 2026-11-05)

Everything except S3, Docker and your own Mac has now run for real, in GitHub Actions on real BTS data:

| Part | Tested? |
|---|---|
| CI on every push (synthetic data): lint, ingest + idempotency, 31 pytest tests, dbt build twice, export, notebook, sensitivity, app | ✅ Green |
| Real BTS downloads from GitHub's servers | ✅ Work. The S3 fallback is not needed |
| `pipeline/db.py` loader, dbt, export on real data | ✅ Monthly refresh with 3 months, then 12 months (7,049,869 flights). All 60 dbt data tests pass (3 warnings) |
| Statistics notebook incl. the regression | ✅ Ran top to bottom on the real 12-month sample (saved as a run artifact) |
| Streamlit pages | ✅ All 6 AppTest page tests pass against the real 12-month files. **Not yet looked at in a browser** |
| Benchmarks, scorecard sensitivity | ✅ Real results in `docs/benchmarks.md` and `docs/scorecard_sensitivity.md` |
| First real-data bug | Fixed: 1 completed flight had a blank arrival delay, which made `is_on_time` null and failed a test. The failed run published nothing (the guard worked) |
| S3, Docker, running on your Mac | ⚠️ Not run |

---

## Phase 1: Set up your Mac (≈1–2 h)

- [ ] **Get the project from GitHub** (the repo is the master copy now). Replace the old Desktop folder:
  ```bash
  cd ~/Desktop
  mv flight-reliability-analytics flight-reliability-analytics-old   # delete this later
  git clone https://github.com/jonnh01/flight-reliability-analytics.git
  ```
- [ ] **Open the project.** In Terminal:
  ```bash
  cd ~/Desktop/flight-reliability-analytics
  ```
  Open the folder in VS Code (File → Open Folder).
- [ ] **Postgres.** Open Postgres.app and make sure it says *Running*. Then: `createdb flights`
- [ ] **Python environment:**
  ```bash
  python3 --version            # must be 3.11 or newer
  python3 -m venv .venv
  source .venv/bin/activate    # run this in every new Terminal window
  pip install -r requirements.txt
  ```
- [ ] **Settings:** `cp .env.example .env`, open `.env`, set `PGUSER` to the output of `whoami`. Keep `MONTHS_BACK=3` for now.
- [ ] **Check the connection:** `psql -d flights -c "select 1"`
- [ ] **Dry run on synthetic data** (proves everything works before touching real data):
  ```bash
  make sample-data
  make ingest-offline
  make dbt-build               # should end with all tests passing
  python -m pipeline.export --synthetic
  make test
  make app                     # opens http://localhost:8501 with a red "synthetic" banner
  ```
  If anything errors, paste the error to Claude and fix it before moving on.
- [ ] **Wipe the synthetic data** so it never mixes with real data:
  ```bash
  make reset-db
  rm -rf data/landing data/cache data/archive data/marts/* data/tableau data/analysis
  ```

## Phase 2: Real BTS data (≈2–3 h)

- [ ] **Check the download link works.** Paste this into your browser. A ZIP should download:
  `https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_7.zip`
  If it doesn't, download a month by hand from transtats.bts.gov, put the ZIP in `data/landing/` (keep the `_2026_7.zip` ending), and add `--offline` to the ingest command.
- [ ] **One month:** set `MONTHS_BACK=1` in `.env`, then `python -m pipeline.ingest`. The log prints the row count. Open the CSV in the ZIP and confirm it has the same number of rows.
- [ ] `make dbt-build`. Read every warning and failure. Real data will surface things the synthetic data didn't (see `docs/runbook.md`).
- [ ] **Three months:** `MONTHS_BACK=3`, run ingest again, then **run it a second time.** It must say `no_new_data` (idempotency).
- [ ] Run the profiling queries in `docs/data_quality.md` and fill in its table.
- [ ] Read `dbt/models/staging/stg_bts__flights.sql` and `int_flights__enriched.sql` until you can explain every line. Rewrite one query yourself.

## Phase 3: GitHub (≈30 min)

- [x] Repo created and pushed by Claude: https://github.com/jonnh01/flight-reliability-analytics
- [ ] Before every commit you make: `git status` and check `.env` is NOT listed.

## Phase 4: Scale up + analysis (≈4–6 h)

- [x] 12 months loaded and tested by the Monthly refresh workflow (7,049,869 rows). Decision: stay at 12, not 24.
- [ ] `make export` (real data, no `--synthetic`).
- [x] Benchmarks and sensitivity ran on the real data (Monthly refresh with *run_analysis* ticked). Read `docs/benchmarks.md` and `docs/scorecard_sensitivity.md` until you can explain every number.
- [ ] Run the notebook (`jupyter notebook analysis/01_statistical_analysis.ipynb`, Restart & Run All). Write the findings section yourself.
- [ ] Write `docs/case_study.md` about one real problem the data shows.
- [ ] Add 2–4 findings to `FINDINGS` in `app/views/findings.py`.

## Phase 5: AWS S3 (optional, ≈1 h)

- [ ] Follow `docs/aws_setup.md`: budget alert **first**, then bucket, IAM user, keys in `.env` and GitHub secrets.
- [ ] `python -m pipeline.ingest`. The log should say `archived to s3://…`.

## Phase 6: Docker (≈1 h)

- [ ] Claude couldn't check whether Docker is on your Mac (it can only see the project folder). Open Terminal and run `docker --version`. If it's not found, install **Docker Desktop for Mac** from docker.com (choose Apple chip or Intel to match your Mac) and open it once.
- [ ] `docker compose up -d db && docker compose run --rm pipeline`, then `docker compose up app`.

## Phase 7: Go live (≈1 h)

- [x] Real `data/marts/` files are committed (the Monthly refresh workflow does this).
- [ ] **share.streamlit.io** → sign in with GitHub → *Create app* → your repo, branch `main`, file `app/streamlit_app.py` → Deploy.
- [ ] Open the public link in a private browser window. Check every page.
- [ ] **Put the link on your resume and LinkedIn now.** Don't wait for the rest.

## Phase 8: Automation (≈1–2 h)

- [x] Monthly refresh with `months_back = 3`: green, committed real `data/marts`.
- [x] Monthly refresh with `months_back = 12` (the new default): green after one fix.
- [ ] Do the four failure tests at the bottom of `docs/runbook.md`.
- [ ] Only after these pass may you say "automated monthly refresh" anywhere.

## Phase 9: Tableau (≈3–4 h)

- [ ] Follow `docs/tableau_guide.md`. Publish. Make sure the numbers match the Streamlit app.

## Phase 10: Finish (≈2–3 h)

- [ ] Fill every `_placeholder_` in `README.md` with real numbers and links. Add a screenshot.
- [ ] Ask a friend to clone the repo and follow "Run it yourself". Fix anything that confuses them.
- [ ] Resume bullets: fill the brackets only with numbers from `docs/benchmarks.md`, dbt's test count, the real row count, and your notebook.
- [ ] Practice explaining aloud: the grain, incremental delete+insert, the shrinkage formula, the LAG() cascade query, and why you report effect sizes.
