-- The loaded months must be continuous (no gap like Jan, Feb, Apr). A gap would make
-- month-over-month charts and the scorecard window silently wrong.

with months as (
    select year_month, to_date(year_month::text || '01', 'YYYYMMDD') as month_start
    from {{ source('raw', 'load_log') }}
),

ordered as (
    select
        year_month,
        month_start,
        lag(month_start) over (order by month_start) as previous_month_start
    from months
)

select year_month, previous_month_start
from ordered
where previous_month_start is not null
  and month_start <> (previous_month_start + interval '1 month')::date
