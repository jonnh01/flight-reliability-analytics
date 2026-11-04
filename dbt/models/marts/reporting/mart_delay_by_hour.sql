-- Network delay profile by scheduled departure hour and month: do delays build up during the day?

select
    year_month,
    dep_hour,
    time_of_day,
    count(*)                                                        as scheduled_flights,
    round(avg(is_on_time::int), 4)                                  as on_time_rate,
    round(avg(dep_delay_min) filter (where not is_cancelled), 2)    as avg_dep_delay_min,
    round(avg(arr_delay_min) filter (where is_completed), 2)        as avg_arr_delay_min,
    round(avg(is_arr_delayed_15::int) filter (where is_completed), 4) as delay_15_rate,
    coalesce(sum(late_aircraft_delay_min), 0)                       as late_aircraft_delay_min,
    coalesce(sum(total_cause_delay_min), 0)                         as total_cause_delay_min
from {{ ref('fct_flights') }}
group by year_month, dep_hour, time_of_day
