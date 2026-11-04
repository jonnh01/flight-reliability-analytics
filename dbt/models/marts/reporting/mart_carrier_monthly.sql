-- Carrier x month KPIs. Rates use the denominators in docs/metric_definitions.md.

select
    f.carrier_code,
    c.carrier_name,
    f.year_month,
    count(*)                                                        as scheduled_flights,
    count(*) filter (where f.is_completed)                          as completed_flights,
    count(*) filter (where f.is_cancelled)                          as cancelled_flights,
    count(*) filter (where f.is_diverted)                           as diverted_flights,
    count(*) filter (where f.is_on_time)                            as on_time_flights,
    count(*) filter (where f.is_arr_delayed_15)                     as delayed_15_flights,
    count(*) filter (where f.is_significant_delay)                  as delayed_60_flights,

    round(avg(f.is_on_time::int), 4)                                as on_time_rate,
    round(avg(f.is_cancelled::int), 4)                              as cancellation_rate,
    round(avg(f.is_arr_delayed_15::int) filter (where f.is_completed), 4) as delay_15_rate,
    round(avg(f.arr_delay_min) filter (where f.is_completed), 2)    as avg_arr_delay_min,
    percentile_cont(0.9) within group (order by f.arr_delay_min)
        filter (where f.is_completed)                               as p90_arr_delay_min,

    coalesce(sum(f.carrier_delay_min), 0)                           as carrier_delay_min,
    coalesce(sum(f.weather_delay_min), 0)                           as weather_delay_min,
    coalesce(sum(f.nas_delay_min), 0)                               as nas_delay_min,
    coalesce(sum(f.security_delay_min), 0)                          as security_delay_min,
    coalesce(sum(f.late_aircraft_delay_min), 0)                     as late_aircraft_delay_min,
    round(sum(f.airline_controllable_delay_min)::numeric
          / nullif(sum(f.total_cause_delay_min), 0), 4)             as controllable_delay_share
from {{ ref('fct_flights') }} as f
join {{ ref('dim_carrier') }} as c using (carrier_code)
group by f.carrier_code, c.carrier_name, f.year_month
