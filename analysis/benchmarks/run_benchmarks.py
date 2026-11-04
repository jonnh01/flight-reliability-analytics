"""Measure query speed before and after indexing, and write docs/benchmarks.md.

    python analysis/benchmarks/run_benchmarks.py --runs 5

For each benchmark query:
  1. drop the project's indexes on marts.fct_flights      -> "before"
  2. run EXPLAIN (ANALYZE, BUFFERS) several times, keep the median execution time
  3. create the indexes and ANALYZE                        -> "after", measured the same way
  4. check both versions return identical results
Every number in the report is measured on YOUR machine and data - nothing is estimated.
Run it on the full dataset (12-24 months) for numbers worth putting on a resume.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline import db  # noqa: E402
from pipeline.config import get_settings  # noqa: E402

INDEXES = {
    "ix_fct_flights_carrier_month": "(carrier_code, year_month)",
    "ix_fct_flights_origin_month": "(origin_airport_code, year_month)",
    "ix_fct_flights_tail_rotation": "(tail_number, flight_date, scheduled_dep_at) where not is_cancelled",
}

# Representative dashboard / analyst questions. %(...)s values are filled from the data.
QUERIES = {
    "Q1 one carrier's monthly trend": """
        select year_month, count(*), avg(is_on_time::int)
        from marts.fct_flights
        where carrier_code = %(carrier)s
        group by year_month order by year_month""",
    "Q2 one airport, latest 3 months, by carrier": """
        select carrier_code, count(*), avg(arr_delay_min) filter (where is_completed)
        from marts.fct_flights
        where origin_airport_code = %(airport)s and year_month >= %(recent_month)s
        group by carrier_code""",
    "Q3 one aircraft's rotation chain (LAG)": """
        select flight_id, scheduled_dep_at, arr_delay_min,
               lag(arr_delay_min) over (partition by tail_number, flight_date order by scheduled_dep_at)
        from marts.fct_flights
        where tail_number = %(tail)s and flight_date = %(day)s and not is_cancelled""",
}


def pick_parameters(conn) -> dict:
    """Use real values from the data so the benchmark reflects real usage."""
    carrier = conn.execute(
        "select carrier_code from marts.fct_flights group by 1 order by count(*) asc limit 1 offset 2"
    ).fetchone()[0]
    airport = conn.execute(
        "select origin_airport_code from marts.fct_flights group by 1 order by count(*) desc limit 1 offset 5"
    ).fetchone()[0]
    latest = conn.execute("select max(year_month) from marts.fct_flights").fetchone()[0]
    recent = conn.execute(
        "select min(year_month) from (select distinct year_month from marts.fct_flights "
        "order by year_month desc limit 3) m"
    ).fetchone()[0]
    tail, day = conn.execute(
        "select tail_number, flight_date from marts.fct_flights where tail_number is not null "
        "and year_month = %s group by 1, 2 order by count(*) desc limit 1",
        (latest,),
    ).fetchone()
    return {"carrier": carrier, "airport": airport, "recent_month": recent, "tail": tail, "day": day}


def measure(conn, sql: str, params: dict, runs: int) -> tuple[float, str]:
    times, plan_root = [], ""
    conn.execute(sql, params).fetchall()  # warm-up run: loads data into cache
    for _ in range(runs):
        plan = conn.execute(f"explain (analyze, buffers, format json) {sql}", params).fetchone()[0]
        plan = plan if isinstance(plan, list) else json.loads(plan)
        times.append(plan[0]["Execution Time"])
        plan_root = describe(plan[0]["Plan"])
    return statistics.median(times), plan_root


def describe(node: dict) -> str:
    """Short text of the scan types used, e.g. 'Seq Scan' or 'Bitmap Index Scan'."""
    found, stack = [], [node]
    while stack:
        current = stack.pop()
        if "Scan" in current["Node Type"]:
            found.append(current["Node Type"])
        stack.extend(current.get("Plans", []))
    return ", ".join(sorted(set(found)))


def set_indexes(conn, present: bool) -> None:
    for name, columns in INDEXES.items():
        if present:
            conn.execute(f"create index if not exists {name} on marts.fct_flights {columns}")
        else:
            conn.execute(f"drop index if exists marts.{name}")
    conn.execute("analyze marts.fct_flights")
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    settings = get_settings()

    with db.connect(settings) as conn:
        rows = conn.execute("select count(*) from marts.fct_flights").fetchone()[0]
        params = pick_parameters(conn)
        results = []
        for label, sql in QUERIES.items():
            set_indexes(conn, present=False)
            before_ms, before_plan = measure(conn, sql, params, args.runs)
            before_rows = sorted(map(str, conn.execute(sql, params).fetchall()))
            set_indexes(conn, present=True)
            after_ms, after_plan = measure(conn, sql, params, args.runs)
            after_rows = sorted(map(str, conn.execute(sql, params).fetchall()))
            results.append((label, before_ms, before_plan, after_ms, after_plan, before_rows == after_rows))
            print(f"{label}: {before_ms:.1f} ms -> {after_ms:.1f} ms")

    lines = [
        "# Query performance benchmarks",
        "",
        f"Measured {datetime.now():%Y-%m-%d %H:%M} on {platform.platform()} against "
        f"**{rows:,} rows** in `marts.fct_flights`. Median of {args.runs} runs of "
        "`EXPLAIN (ANALYZE, BUFFERS)` after one warm-up run. Generated by "
        "`analysis/benchmarks/run_benchmarks.py`.",
        "",
        "| Query | Before (ms) | Plan before | After (ms) | Plan after | Speed-up | Same results |",
        "|---|---:|---|---:|---|---:|---|",
    ]
    for label, b, bp, a, ap, same in results:
        lines.append(f"| {label} | {b:.1f} | {bp} | {a:.1f} | {ap} | {b / a:.1f}x | {'yes' if same else 'NO'} |")
    lines += [
        "",
        "Indexes tested:",
        "",
        *[f"- `{name}` on `fct_flights {cols}`" for name, cols in INDEXES.items()],
        "",
        f"Parameters used: `{params}`",
    ]
    out = ROOT / "docs" / "benchmarks.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
