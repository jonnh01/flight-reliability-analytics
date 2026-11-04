{#
  Fact table. Grain: ONE ROW PER SCHEDULED FLIGHT (including cancelled and diverted ones).

  Incremental strategy (the part interviewers ask about):
  - Each run only processes rows whose _loaded_at is newer than anything already here,
    i.e. months the loader just added or reloaded.
  - unique_key = year_month with delete+insert: dbt first deletes every row of those
    months, then inserts the fresh copy. A month BTS revised is replaced whole, never
    duplicated, and rows BTS removed disappear too.
  - The post-hook removes months the loader pruned from the rolling window.
  - `dbt build --full-refresh` rebuilds everything from scratch.
#}
{{
  config(
    materialized='incremental',
    unique_key='year_month',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    post_hook=[
      "delete from {{ this }} where year_month not in (select year_month from {{ source('raw', 'load_log') }})",
      "create index if not exists ix_fct_flights_carrier_month on {{ this }} (carrier_code, year_month)",
      "create index if not exists ix_fct_flights_origin_month on {{ this }} (origin_airport_code, year_month)",
      "create index if not exists ix_fct_flights_tail_rotation on {{ this }} (tail_number, flight_date, scheduled_dep_at) where not is_cancelled",
      "analyze {{ this }}"
    ]
  )
}}

select
    flight_id,
    year_month,
    flight_date,                     -- joins to dim_date.date_day
    carrier_code,                    -- joins to dim_carrier
    origin_airport_code,             -- joins to dim_airport
    dest_airport_code,               -- joins to dim_airport
    route_key,                       -- joins to dim_route
    tail_number,
    flight_number,
    scheduled_dep_at,
    scheduled_arr_at,
    dep_hour,
    time_of_day,
    distance_miles,
    distance_band,

    dep_delay_min,
    arr_delay_min,
    is_on_time,
    is_arr_delayed_15,
    is_significant_delay,
    is_cancelled,
    cancellation_code,
    is_diverted,
    is_completed,

    carrier_delay_min,
    weather_delay_min,
    nas_delay_min,
    security_delay_min,
    late_aircraft_delay_min,
    airline_controllable_delay_min,
    total_cause_delay_min,

    leg_number_of_day,
    prev_leg_flight_id,
    prev_leg_arr_delay_min,
    scheduled_turn_min,
    is_rotation_consistent,

    loaded_at
from {{ ref('int_flights__enriched') }}

{% if is_incremental() %}
where loaded_at > (select coalesce(max(loaded_at), '1900-01-01'::timestamptz) from {{ this }})
{% endif %}
