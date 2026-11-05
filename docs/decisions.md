# Decision log

"Chose X over Y because Z." Add a line every time you make a real choice. This file is your interview prep.

| Date | Decision | Alternatives | Why |
|---|---|---|---|
| 2026-10-30 | BTS on-time performance data | Olist e-commerce | Real, large (~500k+ rows/month), updates monthly so automation is real; Olist is static and overused |
| 2026-10-30 | dbt Core on PostgreSQL | Plain SQL scripts | Tests, documentation and lineage built in; standard analytics engineering tool |
| 2026-11-04 | Develop on 1-3 months, then expand to 12, then 24 | Load 24 months on day one | Faster feedback while learning; scale once the pipeline is proven |
| 2026-11-04 | Raw layer stores every column as text | Typed raw tables | Loads never fail on surprising values; typing is tested in dbt staging |
| 2026-11-04 | Replace whole months (delete + COPY in one transaction), skip unchanged files by SHA-256 | Row-level upserts | Simple, idempotent, handles BTS revisions; months are the natural unit of the source |
| 2026-11-04 | Incremental fact table with `unique_key = year_month`, delete+insert | Full rebuild every run | Only new/revised months are processed; revised months are replaced cleanly |
| 2026-11-04 | On-time rate denominator = all scheduled flights | Completed flights only | Cancelling flights must not improve a carrier's reliability score |
| 2026-11-04 | Shrinkage (k = 300) for the scorecard | Minimum-volume filter only; Wilson lower bound | Keeps every pair above 100 flights while stopping small samples from dominating; Wilson kept as a comparison |
| 2026-11-04 | S3 as an optional raw archive | Required S3; no archive | GitHub runners have no persistent storage; optional keeps local development unblocked |
| 2026-11-04 | Streamlit reads Parquet extracts | Hosted database | Free hosting, nothing to secure, fast |
| 2026-11-04 | Excel workbook dropped from v2 scope | Keep it | Time goes to Priority 1-3 items; can return later |
| 2026-11-05 | Keep 12 months of history (`months_back` default 12) | 24 months | Jon's call. 12 months already covers the scorecard's trailing-12-month window |
| 2026-11-05 | A completed flight with a blank arrival delay uses BTS's ArrDel15 flag, else counts as not on time; a warning test counts these flights | Drop the row; let the build fail | Found by the first 12-month run (1 flight in 7,049,869). Keeps raw = fact reconciliation intact and keeps the issue visible |
| 2026-11-05 | Benchmarks, sensitivity and the notebook run inside the Monthly refresh workflow (optional `run_analysis`) | Run them on a laptop | Same real data the app shows, a named machine, and the reports are committed automatically |
| | _your next decision_ | | |
