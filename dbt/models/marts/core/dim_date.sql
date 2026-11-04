-- One row per calendar day covered by the loaded data.

with bounds as (
    select min(flight_date) as first_day, max(flight_date) as last_day
    from {{ ref('stg_bts__flights') }}
),

days as (
    select generate_series(first_day, last_day, interval '1 day')::date as date_day
    from bounds
)

select
    d.date_day,
    extract(year from d.date_day)::int                   as year,
    extract(quarter from d.date_day)::int                as quarter,
    extract(month from d.date_day)::int                  as month,
    (extract(year from d.date_day) * 100 + extract(month from d.date_day))::int as year_month,
    to_char(d.date_day, 'Mon YYYY')                      as month_label,
    extract(day from d.date_day)::int                    as day_of_month,
    extract(isodow from d.date_day)::int                 as day_of_week,   -- 1 = Monday
    to_char(d.date_day, 'Dy')                            as day_name,
    extract(isodow from d.date_day) in (6, 7)            as is_weekend,
    h.holiday_date is not null                           as is_holiday,
    h.holiday_name
from days as d
left join {{ ref('us_federal_holidays') }} as h on h.holiday_date = d.date_day
