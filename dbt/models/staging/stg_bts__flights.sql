-- Staging: one row per raw BTS row, renamed, typed and parsed. No business rules here.

with source as (
    select * from {{ source('raw', 'bts_flights') }}
),

typed as (
    select
        _year_month                                         as year_month,
        {{ parse_flight_date('flight_date') }}              as flight_date,
        upper(trim(reporting_airline))                      as carrier_code,
        nullif(upper(trim(tail_number)), '')                as tail_number,
        {{ to_int('flight_number') }}                       as flight_number,
        upper(trim(origin))                                 as origin_airport_code,
        nullif(trim(origin_city_name), '')                  as origin_city_name,
        nullif(trim(origin_state), '')                      as origin_state,
        upper(trim(dest))                                   as dest_airport_code,
        nullif(trim(dest_city_name), '')                    as dest_city_name,
        nullif(trim(dest_state), '')                        as dest_state,

        -- local clock times as minutes after midnight (see macros/bts_parsing.sql)
        {{ hhmm_to_minutes('crs_dep_time') }}               as crs_dep_minutes,
        {{ hhmm_to_minutes('dep_time') }}                   as dep_minutes,
        {{ hhmm_to_minutes('crs_arr_time') }}               as crs_arr_minutes,
        {{ hhmm_to_minutes('arr_time') }}                   as arr_minutes,

        {{ to_int('dep_delay') }}                           as dep_delay_min,
        {{ to_int('arr_delay') }}                           as arr_delay_min,
        {{ to_bool('arr_del15') }}                          as is_arr_delayed_15,
        coalesce({{ to_bool('cancelled') }}, false)         as is_cancelled,
        nullif(upper(trim(cancellation_code)), '')          as cancellation_code,
        coalesce({{ to_bool('diverted') }}, false)          as is_diverted,
        {{ to_int('crs_elapsed_time') }}                    as crs_elapsed_min,
        {{ to_int('actual_elapsed_time') }}                 as actual_elapsed_min,
        {{ to_int('distance') }}                            as distance_miles,

        -- delay causes: BTS fills these ONLY when the flight arrived 15+ min late.
        -- Blank means "not applicable", so they stay null rather than becoming 0.
        {{ to_int('carrier_delay') }}                       as carrier_delay_min,
        {{ to_int('weather_delay') }}                       as weather_delay_min,
        {{ to_int('nas_delay') }}                           as nas_delay_min,
        {{ to_int('security_delay') }}                      as security_delay_min,
        {{ to_int('late_aircraft_delay') }}                 as late_aircraft_delay_min,

        _source_file                                        as source_file,
        _loaded_at                                          as loaded_at
    from source
)

select
    -- Surrogate key: the natural identity of a scheduled flight.
    md5(concat_ws('|',
        flight_date, carrier_code, flight_number, origin_airport_code,
        dest_airport_code, crs_dep_minutes
    ))                                                       as flight_id,
    *,
    -- scheduled departure as a local timestamp ('2400' rolls to the next day)
    flight_date + make_interval(mins => crs_dep_minutes)     as scheduled_dep_at,
    -- scheduled arrival: an arrival clock time earlier than departure means it lands
    -- the next day (red-eyes). Local times, so time-zone changes are not adjusted.
    flight_date
        + make_interval(mins => crs_arr_minutes)
        + case when crs_arr_minutes < crs_dep_minutes then interval '1 day' else interval '0' end
                                                             as scheduled_arr_at
from typed
