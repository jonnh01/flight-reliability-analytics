-- One row per airport that appears as an origin or a destination.

with appearances as (
    select origin_airport_code as airport_code, origin_city_name as city_name,
           origin_state as state, flight_date, 1 as is_departure
    from {{ ref('stg_bts__flights') }}
    union all
    select dest_airport_code, dest_city_name, dest_state, flight_date, 0
    from {{ ref('stg_bts__flights') }}
),

latest_name as (
    -- names occasionally change; keep the most recent spelling
    select distinct on (airport_code) airport_code, city_name, state
    from appearances
    order by airport_code, flight_date desc
),

volume as (
    select airport_code, sum(is_departure) as departures
    from appearances
    group by airport_code
)

select
    v.airport_code,
    n.city_name,
    n.state,
    v.departures,
    rank() over (order by v.departures desc)                               as departures_rank,
    rank() over (order by v.departures desc) <= {{ var('hub_top_n') }}   as is_hub
from volume as v
join latest_name as n using (airport_code)
