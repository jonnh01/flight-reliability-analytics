-- Reconciliation: every month must have exactly as many rows in fct_flights as in the raw
-- table and as the loader recorded in load_log. Any row returned = a mismatch = failure.

with raw_counts as (
    select _year_month as year_month, count(*) as raw_rows
    from {{ source('raw', 'bts_flights') }}
    group by 1
),

fact_counts as (
    select year_month, count(*) as fact_rows
    from {{ ref('fct_flights') }}
    group by 1
),

logged as (
    select year_month, row_count as logged_rows
    from {{ source('raw', 'load_log') }}
)

select
    coalesce(r.year_month, f.year_month, l.year_month) as year_month,
    r.raw_rows,
    f.fact_rows,
    l.logged_rows
from raw_counts as r
full outer join fact_counts as f using (year_month)
full outer join logged as l using (year_month)
where r.raw_rows is distinct from f.fact_rows
   or r.raw_rows is distinct from l.logged_rows
