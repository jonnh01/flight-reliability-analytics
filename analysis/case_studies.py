"""Numbers behind the two case studies, measured straight from the warehouse.

    python analysis/case_studies.py

Writes docs/case_study_data.md. Every table in docs/case_study.md comes from this file,
so the case studies can be regenerated (and re-checked) after every monthly refresh.

  A. San Francisco (SFO) arrivals: why flights INTO SFO are late more often than flights OUT
  B. PSA Airlines (OH): why one regional carrier dominates the reliability priority list
"""
from __future__ import annotations

import numbers
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import db  # noqa: E402
from pipeline.config import get_settings  # noqa: E402
from pipeline.export import query_df  # noqa: E402

CAUSES = ["carrier", "late_aircraft", "nas", "weather", "security"]
CAUSE_SHARES = ",\n    ".join(
    f"round(sum({c}_delay_min)::numeric / nullif(sum(total_cause_delay_min), 0), 4) as {c}_share"
    for c in CAUSES
)
KPIS = f"""
    count(*)                                                        as flights,
    round(avg(is_on_time::int), 4)                                  as on_time_rate,
    round(avg(is_cancelled::int), 4)                                as cancellation_rate,
    round(avg(arr_delay_min) filter (where is_completed), 1)        as avg_arr_delay_min,
    {CAUSE_SHARES}
"""
PEERS = ["SFO", "LAX", "SEA", "SAN", "LAS", "DEN", "PHX"]

QUERIES: dict[str, tuple[str, str]] = {
    # ---------------- A. SFO arrivals ----------------
    "A1": ("SFO and western peers: arrivals vs departures", f"""
        select airport, direction, {KPIS}
        from (
            select dest_airport_code as airport, 'arriving' as direction, * from marts.fct_flights
            where dest_airport_code = any(%(peers)s)
            union all
            select origin_airport_code, 'departing', * from marts.fct_flights
            where origin_airport_code = any(%(peers)s)
        ) f
        group by airport, direction
        order by airport, direction"""),
    "A2": ("Flights arriving at SFO by month", f"""
        select year_month, {KPIS}
        from marts.fct_flights where dest_airport_code = 'SFO'
        group by year_month order by year_month"""),
    "A3": ("Flights arriving at SFO by scheduled arrival hour (local time)", f"""
        select extract(hour from scheduled_arr_at)::int as arrival_hour, {KPIS}
        from marts.fct_flights where dest_airport_code = 'SFO'
        group by 1 having count(*) >= 1000 order by 1"""),
    "A4": ("Flights arriving at SFO by carrier (1,000+ flights)", f"""
        select carrier_code, {KPIS}
        from marts.fct_flights where dest_airport_code = 'SFO'
        group by carrier_code having count(*) >= 1000 order by on_time_rate"""),
    "A5": ("Same carriers, all their other arrivals (not SFO), for comparison", f"""
        select carrier_code, {KPIS}
        from marts.fct_flights
        where dest_airport_code <> 'SFO'
          and carrier_code in (select carrier_code from marts.fct_flights where dest_airport_code = 'SFO'
                               group by 1 having count(*) >= 1000)
        group by carrier_code order by on_time_rate"""),
    "A6": ("Routes into SFO with 2,000+ flights, worst first", f"""
        select origin_airport_code as origin, {KPIS}
        from marts.fct_flights where dest_airport_code = 'SFO'
        group by origin_airport_code having count(*) >= 2000 order by on_time_rate limit 10"""),
    # ---------------- B. PSA Airlines ----------------
    "B1": ("PSA Airlines (OH) vs all other carriers", f"""
        select case when carrier_code = 'OH' then 'PSA (OH)' else 'All other carriers' end as carrier, {KPIS}
        from marts.fct_flights group by 1 order by 1 desc"""),
    "B2": ("Why flights were cancelled: PSA vs all other carriers (share of cancellations)", """
        select case when carrier_code = 'OH' then 'PSA (OH)' else 'All other carriers' end as carrier,
               count(*) as cancelled_flights,
               round(avg((cancellation_code = 'A')::int), 4) as carrier_caused,
               round(avg((cancellation_code = 'B')::int), 4) as weather,
               round(avg((cancellation_code = 'C')::int), 4) as national_air_system,
               round(avg((cancellation_code = 'D')::int), 4) as security
        from marts.fct_flights where is_cancelled group by 1 order by 1 desc"""),
    "B3": ("PSA by month vs the rest of the network", """
        select year_month,
               round(avg(is_on_time::int) filter (where carrier_code = 'OH'), 4)          as psa_on_time,
               round(avg(is_on_time::int) filter (where carrier_code <> 'OH'), 4)         as others_on_time,
               round(avg(is_cancelled::int) filter (where carrier_code = 'OH'), 4)        as psa_cancelled,
               round(avg(is_cancelled::int) filter (where carrier_code <> 'OH'), 4)       as others_cancelled
        from marts.fct_flights group by year_month order by year_month"""),
    "B4": ("PSA's 10 busiest departure airports vs other carriers at the same airport", """
        with psa as (
            select origin_airport_code as airport, count(*) as psa_flights,
                   round(avg(is_on_time::int), 4) as psa_on_time,
                   round(avg(is_cancelled::int), 4) as psa_cancelled
            from marts.fct_flights where carrier_code = 'OH'
            group by 1 order by psa_flights desc limit 10
        ), others as (
            select origin_airport_code as airport,
                   round(avg(is_on_time::int), 4) as others_on_time,
                   round(avg(is_cancelled::int), 4) as others_cancelled
            from marts.fct_flights where carrier_code <> 'OH'
            and origin_airport_code in (select airport from psa) group by 1
        )
        select * from psa join others using (airport) order by psa_flights desc"""),
    "B5": ("Late inbound aircraft: share of next flights arriving 15+ late, PSA vs others", """
        select case when carrier_code = 'OH' then 'PSA (OH)' else 'All other carriers' end as carrier,
               case when prev_leg_arr_delay_min >= 15 then 'previous leg 15+ late'
                    else 'previous leg on time' end as previous_leg,
               count(*) as flights,
               round(avg(is_arr_delayed_15::int), 4) as share_late
        from marts.fct_flights
        where is_completed and prev_leg_arr_delay_min is not null and coalesce(is_rotation_consistent, true)
        group by 1, 2 order by 1 desc, 2 desc"""),
    "B6": ("PSA's place on the reliability scorecard", """
        select carrier_code, count(*) as ranked_pairs,
               count(*) filter (where is_priority) as in_top_20,
               round(avg(risk_rank)) as average_rank
        from marts.mart_reliability_scorecard group by 1 order by in_top_20 desc, average_rank"""),
}

RATE_COLUMNS = ("rate", "share", "on_time", "cancelled", "carrier_caused", "weather", "national_air_system", "security")


def to_markdown(frame: pd.DataFrame) -> str:
    """Small markdown table without extra dependencies. Rates and shares print as percentages."""
    def fmt(col, value):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        if col.endswith(RATE_COLUMNS) and isinstance(value, numbers.Real) and abs(value) <= 1:
            return f"{value:.1%}"
        if isinstance(value, numbers.Integral) and not col.endswith(("hour", "month")):
            return f"{value:,}"
        return str(value)
    head = "| " + " | ".join(frame.columns) + " |"
    sep = "|" + "|".join("---" for _ in frame.columns) + "|"
    rows = ["| " + " | ".join(fmt(c, v) for c, v in zip(frame.columns, row)) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def main() -> None:
    settings = get_settings()
    sections = [
        "# Case study data",
        "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M} by `analysis/case_studies.py` from `marts.fct_flights`. "
        "Rates use the project's definitions (`docs/metric_definitions.md`): on-time = completed and "
        "arrived <15 minutes late, out of all scheduled flights. Cause shares are shares of delay minutes "
        "that airlines attributed to a cause (flights 15+ minutes late only).",
    ]
    with db.connect(settings) as conn:
        months = conn.execute("select min(year_month), max(year_month), count(*) from marts.fct_flights").fetchone()
        sections.append(f"\nData: {months[0]}–{months[1]}, {months[2]:,} scheduled flights.\n")
        for key, (title, sql) in QUERIES.items():
            frame = query_df(conn, sql, {"peers": PEERS} if "%(peers)s" in sql else None)
            sections += [f"## {key}. {title}", "", to_markdown(frame), ""]
            print(f"{key}: {len(frame)} rows")
    out = ROOT / "docs" / "case_study_data.md"
    out.write_text("\n".join(sections))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
