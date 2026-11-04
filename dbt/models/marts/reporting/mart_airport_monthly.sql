-- Origin airport x month KPIs (departure-side view of each airport).

select
    f.origin_airport_code                                           as airport_code,
    a.city_name,
    a.state,
    a.is_hub,
    f.year_month,
    count(*)                                                        as scheduled_departures,
    count(*) filter (where f.is_cancelled)                          as cancelled_flights,
    round(avg(f.is_on_time::int), 4)                                as on_time_rate,
    round(avg(f.is_cancelled::int), 4)                              as cancellation_rate,
    round(avg(f.dep_delay_min) filter (where not f.is_cancelled), 2) as avg_dep_delay_min,
    round(avg(f.arr_delay_min) filter (where f.is_completed), 2)    as avg_arr_delay_min,
    coalesce(sum(f.weather_delay_min), 0)                           as weather_delay_min,
    coalesce(sum(f.nas_delay_min), 0)                               as nas_delay_min,
    coalesce(sum(f.total_cause_delay_min), 0)                       as total_cause_delay_min
from {{ ref('fct_flights') }} as f
join {{ ref('dim_airport') }} as a on a.airport_code = f.origin_airport_code
group by f.origin_airport_code, a.city_name, a.state, a.is_hub, f.year_month
