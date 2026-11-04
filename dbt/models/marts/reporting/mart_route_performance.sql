-- Route-level reliability over the loaded window, with a persistence measure:
-- in how many of its months did the route do worse than the whole network that month?

with route_month as (
    select
        route_key,
        year_month,
        count(*)                          as flights,
        avg(is_on_time::int)              as on_time_rate
    from {{ ref('fct_flights') }}
    group by route_key, year_month
),

network_month as (
    select year_month, avg(is_on_time::int) as network_on_time_rate
    from {{ ref('fct_flights') }}
    group by year_month
),

persistence as (
    select
        rm.route_key,
        count(*)                                                        as months_active,
        count(*) filter (where rm.on_time_rate < nm.network_on_time_rate) as months_below_network
    from route_month as rm
    join network_month as nm using (year_month)
    group by rm.route_key
),

totals as (
    select
        route_key,
        count(*)                                                        as scheduled_flights,
        round(avg(is_on_time::int), 4)                                  as on_time_rate,
        round(avg(is_cancelled::int), 4)                                as cancellation_rate,
        round(avg(arr_delay_min) filter (where is_completed), 2)        as avg_arr_delay_min
    from {{ ref('fct_flights') }}
    group by route_key
)

select
    t.route_key,
    r.origin_airport_code,
    r.dest_airport_code,
    r.distance_miles,
    r.distance_band,
    t.scheduled_flights,
    t.on_time_rate,
    t.cancellation_rate,
    t.avg_arr_delay_min,
    p.months_active,
    p.months_below_network,
    round(p.months_below_network::numeric / p.months_active, 4)        as share_months_below_network
from totals as t
join persistence as p using (route_key)
join {{ ref('dim_route') }} as r using (route_key)
