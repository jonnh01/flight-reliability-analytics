-- Intermediate: business definitions added to every flight, plus aircraft rotation context.
-- All KPI definitions live here once, so every mart counts things the same way.

with flights as (
    select * from {{ ref('stg_bts__flights') }}
),

-- Aircraft rotation: for each plane, its flights that day in scheduled order.
-- LAG() looks one row back = the same aircraft's previous leg.
-- Cancelled legs and flights without a tail number are left out of the rotation.
rotation as (
    select
        flight_id,
        row_number() over w                                        as leg_number_of_day,
        lag(arr_delay_min) over w                                  as prev_leg_arr_delay_min,
        lag(dest_airport_code) over w                              as prev_leg_dest_airport_code,
        lag(flight_id) over w                                      as prev_leg_flight_id,
        extract(epoch from scheduled_dep_at - lag(scheduled_arr_at) over w) / 60
                                                                   as scheduled_turn_min
    from flights
    where tail_number is not null
      and not is_cancelled
    window w as (partition by tail_number, flight_date order by scheduled_dep_at, flight_id)
)

select
    f.*,

    -- time of day of the SCHEDULED departure (what a passenger books)
    (f.crs_dep_minutes / 60) % 24                                  as dep_hour,
    case
        when (f.crs_dep_minutes / 60) % 24 between 5 and 11  then 'morning'
        when (f.crs_dep_minutes / 60) % 24 between 12 and 16 then 'afternoon'
        when (f.crs_dep_minutes / 60) % 24 between 17 and 21 then 'evening'
        else 'night'
    end                                                            as time_of_day,

    -- status flags (see docs/metric_definitions.md)
    not f.is_cancelled and not f.is_diverted                       as is_completed,
    -- On time = completed AND arrived < 15 min late. Cancelled and diverted flights
    -- count as NOT on time, so a carrier cannot look reliable by cancelling.
    -- BTS occasionally leaves the arrival delay blank on a completed flight. Then use its
    -- ArrDel15 flag; if that is blank too, the flight can't be shown on time -> false.
    -- (Without the coalesce, "true AND null" is null and the not_null test fails.)
    (not f.is_cancelled and not f.is_diverted
        and coalesce(f.arr_delay_min < {{ var('on_time_threshold_min') }},
                     not f.is_arr_delayed_15,
                     false))                                       as is_on_time,
    coalesce(f.arr_delay_min >= 60, false)                         as is_significant_delay,

    -- delay minutes the airline controls: its own issues + late inbound aircraft
    case when f.is_arr_delayed_15
         then coalesce(f.carrier_delay_min, 0) + coalesce(f.late_aircraft_delay_min, 0)
    end                                                           as airline_controllable_delay_min,
    case when f.is_arr_delayed_15
         then coalesce(f.carrier_delay_min, 0) + coalesce(f.weather_delay_min, 0)
            + coalesce(f.nas_delay_min, 0) + coalesce(f.security_delay_min, 0)
            + coalesce(f.late_aircraft_delay_min, 0)
    end                                                            as total_cause_delay_min,

    case
        when f.distance_miles < 500  then 'short (<500 mi)'
        when f.distance_miles < 1000 then 'medium (500-999 mi)'
        when f.distance_miles < 2000 then 'long (1000-1999 mi)'
        else 'very long (2000+ mi)'
    end                                                            as distance_band,

    f.origin_airport_code || '-' || f.dest_airport_code            as route_key,

    r.leg_number_of_day,
    r.prev_leg_flight_id,
    r.prev_leg_arr_delay_min,
    r.prev_leg_dest_airport_code,
    r.scheduled_turn_min,
    -- Data check: the previous leg should have landed where this one departs
    (r.prev_leg_dest_airport_code = f.origin_airport_code)          as is_rotation_consistent

from flights as f
left join rotation as r using (flight_id)
-- Intermediate: business definitions added to every flight, plus aircraft rotation context.
-- All KPI definitions live here once, so every mart counts things the same way.

with flights as (
    select * from {{ ref('stg_bts__flights') }}
),

-- Aircraft rotation: for each plane, its flights that day in scheduled order.
-- LAG() looks one row back = the same aircraft's previous leg.
-- Cancelled legs and flights without a tail number are left out of the rotation.
rotation as (
    select
        flight_id,
        row_number() over w                                        as leg_number_of_day,
        lag(arr_delay_min) over w                                  as prev_leg_arr_delay_min,
        lag(dest_airport_code) over w                              as prev_leg_dest_airport_code,
        lag(flight_id) over w                                      as prev_leg_flight_id,
        extract(epoch from scheduled_dep_at - lag(scheduled_arr_at) over w) / 60
                                                                   as scheduled_turn_min
    from flights
    where tail_number is not null
      and not is_cancelled
    window w as (partition by tail_number, flight_date order by scheduled_dep_at, flight_id)
)

select
    f.*,

    -- time of day of the SCHEDULED departure (what a passenger books)
    (f.crs_dep_minutes / 60) % 24                                  as dep_hour,
    case
        when (f.crs_dep_minutes / 60) % 24 between 5 and 11  then 'morning'
        when (f.crs_dep_minutes / 60) % 24 between 12 and 16 then 'afternoon'
        when (f.crs_dep_minutes / 60) % 24 between 17 and 21 then 'evening'
        else 'night'
    end                                                            as time_of_day,

    -- status flags (see docs/metric_definitions.md)
    not f.is_cancelled and not f.is_diverted                       as is_completed,
    -- On time = completed AND arrived < 15 min late. Cancelled and diverted flights
    -- count as NOT on time, so a carrier cannot look reliable by cancelling.
    (not f.is_cancelled and not f.is_diverted
        and f.arr_delay_min < {{ var('on_time_threshold_min') }})  as is_on_time,
    coalesce(f.arr_delay_min >= 60, false)                         as is_significant_delay,

    -- delay minutes the airline controls: its own issues + late inbound aircraft
    case when f.is_arr_delayed_15
         then coalesce(f.carrier_delay_min, 0) + coalesce(f.late_aircraft_delay_min, 0)
    end                                                            as airline_controllable_delay_min,
    case when f.is_arr_delayed_15
         then coalesce(f.carrier_delay_min, 0) + coalesce(f.weather_delay_min, 0)
            + coalesce(f.nas_delay_min, 0) + coalesce(f.security_delay_min, 0)
            + coalesce(f.late_aircraft_delay_min, 0)
    end                                                            as total_cause_delay_min,

    case
        when f.distance_miles < 500  then 'short (<500 mi)'
        when f.distance_miles < 1000 then 'medium (500-999 mi)'
        when f.distance_miles < 2000 then 'long (1000-1999 mi)'
        else 'very long (2000+ mi)'
    end                                                            as distance_band,

    f.origin_airport_code || '-' || f.dest_airport_code            as route_key,

    r.leg_number_of_day,
    r.prev_leg_flight_id,
    r.prev_leg_arr_delay_min,
    r.prev_leg_dest_airport_code,
    r.scheduled_turn_min,
    -- Data check: the previous leg should have landed where this one departs
    (r.prev_leg_dest_airport_code = f.origin_airport_code)          as is_rotation_consistent

from flights as f
left join rotation as r using (flight_id)
