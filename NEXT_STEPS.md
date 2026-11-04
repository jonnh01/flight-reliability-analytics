# Next steps: your manual checklist

The AI-assisted code is written. This file lists **what only you can do**, in order. Tick each box as you go. Times are rough.

## What has and hasn't been tested yet

Claude couldn't install packages or reach the BTS website from its workspace, so testing was partial:

| Part | Tested? |
|---|---|
| All dbt SQL (staging, star schema, incremental loads, every mart, all data tests) | ✅ Ran against a real PostgreSQL 16 on synthetic data. Every test passed, including a reload and a pruned month |
| BTS file reading, column checks, archive logic, what-if math (pytest) | ✅ 22 unit tests pass |
| Stats notebook sections 1–3, scorecard sensitivity script | ✅ Ran on the synthetic marts |
| All 5 dashboard pages | ✅ Ran top to bottom with Streamlit stubbed out (logic only, not the visuals) |
| The Python ↔ Postgres loader (`pipeline/db.py`), dbt itself, Streamlit itself, the regression cell | ⚠️ **Not run yet** (packages unavailable). Your first local run and the GitHub CI run are the real test |
| Real BTS data, S3, Docker, GitHub Actions | ⚠️ Not run. These need your accounts and your machine |

So expect to fix a few small things on the first run. That's normal, and you'll learn the code doing it.

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

- [ ] `MONTHS_BACK=12`, ingest, `make dbt-build`. Note how long each step takes.
- [ ] `MONTHS_BACK=24` if your laptop copes (expect roughly 13–14M rows; check the real number).
- [ ] `make export` (real data, no `--synthetic`).
- [ ] `make benchmark` → read `docs/benchmarks.md`. These are your real before/after numbers.
- [ ] `make sensitivity` → read `docs/scorecard_sensitivity.md`.
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

- [ ] Commit and push the real `data/marts/` files.
- [ ] **share.streamlit.io** → sign in with GitHub → *Create app* → your repo, branch `main`, file `app/streamlit_app.py` → Deploy.
- [ ] Open the public link in a private browser window. Check every page.
- [ ] **Put the link on your resume and LinkedIn now.** Don't wait for the rest.

## Phase 8: Automation (≈1–2 h)

- [ ] GitHub → Actions → **Monthly refresh** → *Run workflow* with `months_back = 3` first. It must go green and commit fresh `data/marts`.
- [ ] Then run it with `24`. Check its run time. If it fails on disk or time, set repository variable `MONTHS_BACK` to `12`.
- [ ] Do the four failure tests at the bottom of `docs/runbook.md`.
- [ ] Only after these pass may you say "automated monthly refresh" anywhere.

## Phase 9: Tableau (≈3–4 h)

- [ ] Follow `docs/tableau_guide.md`. Publish. Make sure the numbers match the Streamlit app.

## Phase 10: Finish (≈2–3 h)

- [ ] Fill every `_placeholder_` in `README.md` with real numbers and links. Add a screenshot.
- [ ] Ask a friend to clone the repo and follow "Run it yourself". Fix anything that confuses them.
- [ ] Resume bullets: fill the brackets only with numbers from `docs/benchmarks.md`, dbt's test count, the real row count, and your notebook.
- [ ] Practice explaining aloud: the grain, incremental delete+insert, the shrinkage formula, the LAG() cascade query, and why you report effect sizes.
