-- A completed (not cancelled, not diverted) flight should always have an arrival delay.
-- BTS occasionally leaves it blank; int_flights__enriched then counts the flight as NOT
-- on time unless BTS's ArrDel15 flag says otherwise. This test lists those flights so the
-- number stays visible: warn on any, fail if it ever becomes common.
{{ config(severity='error', warn_if='>0', error_if='>100') }}

select
    flight_id,
    year_month,
    carrier_code,
    flight_date
from {{ ref('fct_flights') }}
where is_completed
  and arr_delay_min is null
