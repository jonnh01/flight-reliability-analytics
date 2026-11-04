-- BTS rule: for flights 15+ minutes late, the five cause columns add up to the arrival
-- delay. Rows returned break that rule (1-minute tolerance for rounding).
-- Warn on a handful (BTS data is not perfect); fail if it becomes widespread.
{{ config(severity='error', warn_if='>0', error_if='>500') }}

select
    flight_id,
    year_month,
    arr_delay_min,
    total_cause_delay_min
from {{ ref('fct_flights') }}
where is_arr_delayed_15
  and is_completed
  and total_cause_delay_min is not null
  and abs(total_cause_delay_min - arr_delay_min) > 1
