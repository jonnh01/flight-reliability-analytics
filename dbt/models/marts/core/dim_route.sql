-- One row per directional origin-destination pair (ATL-LAX and LAX-ATL are two routes).

select
    route_key,
    min(origin_airport_code)                                       as origin_airport_code,
    min(dest_airport_code)                                         as dest_airport_code,
    -- the most common published distance for the pair
    mode() within group (order by distance_miles)                  as distance_miles,
    mode() within group (order by distance_band)                   as distance_band,
    count(*)                                                       as flights_loaded
from {{ ref('int_flights__enriched') }}
group by route_key
