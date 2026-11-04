-- One-row summary the dashboard shows so viewers know how fresh the data is.

select
    min(f.year_month)                           as first_month,
    max(f.year_month)                           as latest_month,
    count(distinct f.year_month)                as months_loaded,
    count(*)                                    as total_flights,
    count(distinct f.carrier_code)              as carriers,
    count(distinct f.origin_airport_code)       as origin_airports,
    (select max(loaded_at) from {{ source('raw', 'load_log') }}) as last_loaded_at,
    now()                                       as built_at
from {{ ref('fct_flights') }} as f
