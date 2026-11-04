-- One row per airline code seen in the data. First/last month seen makes code changes and
-- mergers visible (a carrier that stops reporting shows an old last_seen_month).

with seen as (
    select
        carrier_code,
        min(year_month) as first_seen_month,
        max(year_month) as last_seen_month,
        count(*)        as flights_loaded
    from {{ ref('stg_bts__flights') }}
    group by carrier_code
)

select
    s.carrier_code,
    coalesce(c.carrier_name, 'Unknown carrier (' || s.carrier_code || ')') as carrier_name,
    coalesce(c.carrier_type, 'unknown')                                   as carrier_type,
    s.first_seen_month,
    s.last_seen_month,
    s.flights_loaded
from seen as s
left join {{ ref('carriers') }} as c using (carrier_code)
