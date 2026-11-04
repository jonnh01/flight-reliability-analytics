-- Cascade analysis: how often is a flight delayed, given how late the SAME aircraft's
-- previous leg arrived? Built on the LAG() rotation fields in int_flights__enriched.
-- This shows association, not proof of cause (see docs/case_study.md).

with legs as (
    select
        carrier_code,
        is_arr_delayed_15,
        dep_delay_min,
        case
            when prev_leg_arr_delay_min is null then '0: first leg of the day'
            when prev_leg_arr_delay_min < 15    then '1: previous leg on time (<15)'
            when prev_leg_arr_delay_min < 60    then '2: previous leg 15-59 late'
            when prev_leg_arr_delay_min < 120   then '3: previous leg 60-119 late'
            else                                     '4: previous leg 120+ late'
        end                                                         as prev_leg_bucket,
        least(leg_number_of_day, 6)                                 as leg_number_capped
    from {{ ref('fct_flights') }}
    where is_completed
      and leg_number_of_day is not null
      and coalesce(is_rotation_consistent, true)  -- skip rotations that do not chain
)

select
    carrier_code,
    prev_leg_bucket,
    leg_number_capped,
    count(*)                                            as flights,
    count(*) filter (where is_arr_delayed_15)           as delayed_15_flights,
    round(avg(is_arr_delayed_15::int), 4)               as delay_15_rate,
    round(avg(dep_delay_min), 2)                        as avg_dep_delay_min
from legs
group by carrier_code, prev_leg_bucket, leg_number_capped
