"""Export the reporting marts for the dashboards.  Run:  python -m pipeline.export

Writes
  data/marts/<mart>.parquet     small files the Streamlit app reads (committed to GitHub)
  data/marts/manifest.json      what was exported, when, and how fresh the data is
  data/tableau/<mart>.csv       the same tables as CSV for Tableau Public
  data/analysis/flights_sample.parquet   random flight-level sample for the stats notebook

Only run this after `dbt build` has passed - the GitHub workflow enforces that order, so
a failed test can never publish bad numbers.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from pipeline import db
from pipeline.config import get_settings
from pipeline.logging_setup import setup_logging

log = logging.getLogger("pipeline.export")

MARTS = [
    "mart_carrier_monthly",
    "mart_airport_monthly",
    "mart_route_performance",
    "mart_delay_causes",
    "mart_delay_by_hour",
    "mart_delay_propagation",
    "mart_reliability_scorecard",
    "mart_whatif_delayed_flights",
    "mart_pipeline_status",
    "dim_carrier",
    "dim_airport",
]

SAMPLE_COLUMNS = """
    f.flight_id, f.year_month, f.flight_date, f.carrier_code, f.origin_airport_code,
    f.dest_airport_code, f.dep_hour, f.time_of_day, f.distance_miles, f.distance_band,
    extract(month from f.flight_date)::int as month, extract(isodow from f.flight_date)::int as day_of_week,
    f.dep_delay_min, f.arr_delay_min, f.is_on_time, f.is_arr_delayed_15, f.is_cancelled,
    f.is_completed, f.leg_number_of_day, f.prev_leg_arr_delay_min, a.is_hub as origin_is_hub
"""


def query_df(conn, sql: str, params=None) -> pd.DataFrame:
    cur = conn.execute(sql, params)
    frame = pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])
    for col in frame.columns:  # Postgres numeric -> Decimal; dashboards want floats
        first = frame[col].dropna().head(1)
        if len(first) and isinstance(first.iloc[0], Decimal):
            frame[col] = frame[col].astype(float)
    return frame


def export(sample_rows: int, synthetic: bool) -> dict:
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level, "export")
    for folder in (settings.marts_dir, settings.tableau_dir, settings.analysis_dir):
        folder.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "synthetic_data": synthetic,
        "tables": {},
    }
    with db.connect(settings) as conn:
        for mart in MARTS:
            frame = query_df(conn, f"select * from marts.{mart}")
            frame.to_parquet(settings.marts_dir / f"{mart}.parquet", index=False)
            frame.to_csv(settings.tableau_dir / f"{mart}.csv", index=False)
            manifest["tables"][mart] = len(frame)
            log.info("exported %-30s %8s rows", mart, f"{len(frame):,}")

        status = query_df(conn, "select * from marts.mart_pipeline_status").iloc[0]
        manifest["latest_month"] = int(status["latest_month"])
        manifest["first_month"] = int(status["first_month"])
        manifest["total_flights"] = int(status["total_flights"])

        total = manifest["total_flights"]
        fraction = min(1.0, sample_rows / total) if total else 1.0
        sample = query_df(
            conn,
            f"select {SAMPLE_COLUMNS} from marts.fct_flights f "
            "join marts.dim_airport a on a.airport_code = f.origin_airport_code "
            "where random() < %s",
            (fraction,),
        )
        sample.to_parquet(settings.analysis_dir / "flights_sample.parquet", index=False)
        manifest["analysis_sample_rows"] = len(sample)
        log.info("exported flight sample: %s rows (%.1f%%)", f"{len(sample):,}", fraction * 100)

    (settings.marts_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export marts to Parquet/CSV.")
    parser.add_argument("--sample-rows", type=int, default=500_000, help="flight-level sample size")
    parser.add_argument("--synthetic", action="store_true",
                        help="label the export as synthetic test data (the app shows a warning)")
    args = parser.parse_args(argv)
    try:
        export(args.sample_rows, args.synthetic)
        return 0
    except Exception:
        log.exception("export failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
