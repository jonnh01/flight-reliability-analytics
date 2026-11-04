-- Inputs for the app's what-if page: every flight in the LATEST month that arrived 15+ min
-- late, with its cause minutes. The app asks "if cause X shrank by N%, how many of these
-- would have arrived under 15 minutes late?" Kept to one month to stay small.

select
    flight_id,
    carrier_code,
    origin_airport_code                         as airport_code,
    time_of_day,
    arr_delay_min,
    coalesce(carrier_delay_min, 0)              as carrier_delay_min,
    coalesce(weather_delay_min, 0)              as weather_delay_min,
    coalesce(nas_delay_min, 0)                  as nas_delay_min,
    coalesce(security_delay_min, 0)             as security_delay_min,
    coalesce(late_aircraft_delay_min, 0)        as late_aircraft_delay_min
from {{ ref('fct_flights') }}
where is_arr_delayed_15
  and is_completed
  and year_month = (select max(year_month) from {{ ref('fct_flights') }})
