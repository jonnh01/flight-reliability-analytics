-- Where delay minutes come from: carrier x origin airport x month, one column per BTS cause.
-- Only flights 15+ minutes late carry cause minutes (BTS rule).

select
    f.carrier_code,
    f.origin_airport_code                                   as airport_code,
    f.year_month,
    count(*) filter (where f.is_arr_delayed_15)             as delayed_15_flights,
    coalesce(sum(f.carrier_delay_min), 0)                   as carrier_delay_min,
    coalesce(sum(f.weather_delay_min), 0)                   as weather_delay_min,
    coalesce(sum(f.nas_delay_min), 0)                       as nas_delay_min,
    coalesce(sum(f.security_delay_min), 0)                  as security_delay_min,
    coalesce(sum(f.late_aircraft_delay_min), 0)             as late_aircraft_delay_min,
    coalesce(sum(f.total_cause_delay_min), 0)               as total_cause_delay_min
from {{ ref('fct_flights') }} as f
group by f.carrier_code, f.origin_airport_code, f.year_month
having count(*) filter (where f.is_arr_delayed_15) > 0
