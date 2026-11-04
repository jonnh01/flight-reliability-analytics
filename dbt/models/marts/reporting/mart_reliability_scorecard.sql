{#
  Volume-adjusted reliability scorecard: one row per carrier x origin airport over the
  trailing `scorecard_months` months. Higher risk_score = less reliable. Rank 1 = look first.

  Small-sample adjustment (empirical-Bayes style shrinkage):
    adjusted rate = (events + k * network_rate) / (flights + k)
  With k = scorecard_prior_flights (300), a pair with 40 flights is pulled strongly toward
  the network average, while a pair with 5,000 flights barely moves. So a carrier with
  12 flights and 100% on time cannot top (or bottom) the ranking by luck.

  The four adjusted metrics are standardised (z-scores) and combined with the weights in
  dbt_project.yml. analysis/scorecard_sensitivity.py checks the ranking holds up when the
  weights change. Full definitions: docs/metric_definitions.md
#}

{% set k = var('scorecard_prior_flights') %}

with latest as (
    select max(year_month) as latest_ym from {{ ref('fct_flights') }}
),

window_bounds as (
    select
        latest_ym,
        (extract(year from d) * 100 + extract(month from d))::int as first_ym
    from latest,
         lateral (select to_date(latest_ym::text || '01', 'YYYYMMDD')
                         - make_interval(months => {{ var('scorecard_months') }} - 1) as d) as s
),

pairs as (
    select
        f.carrier_code,
        f.origin_airport_code                                       as airport_code,
        count(*)                                                    as flights,
        count(*) filter (where f.is_completed)                      as completed_flights,
        count(*) filter (where f.is_on_time)                        as on_time_flights,
        count(*) filter (where f.is_cancelled)                      as cancelled_flights,
        coalesce(sum(f.arr_delay_min) filter (where f.is_completed), 0) as total_arr_delay_min,
        coalesce(sum(f.airline_controllable_delay_min), 0)          as controllable_delay_min,
        coalesce(sum(f.total_cause_delay_min), 0)                   as cause_delay_min
    from {{ ref('fct_flights') }} as f
    cross join window_bounds as w
    where f.year_month between w.first_ym and w.latest_ym
    group by f.carrier_code, f.origin_airport_code
),

priors as (
    -- network-wide averages that small samples are pulled toward
    select
        sum(on_time_flights)::numeric   / sum(flights)                       as p_on_time,
        sum(cancelled_flights)::numeric / sum(flights)                       as p_cancel,
        sum(total_arr_delay_min)::numeric / nullif(sum(completed_flights), 0) as mu_delay,
        sum(controllable_delay_min)::numeric / nullif(sum(cause_delay_min), 0) as p_controllable,
        sum(cause_delay_min)::numeric / sum(flights)                         as cause_min_per_flight
    from pairs
),

adjusted as (
    select
        p.*,
        p.on_time_flights::numeric / p.flights                                     as raw_on_time_rate,
        p.cancelled_flights::numeric / p.flights                                   as raw_cancellation_rate,
        p.total_arr_delay_min::numeric / nullif(p.completed_flights, 0)           as raw_avg_arr_delay_min,
        p.controllable_delay_min::numeric / nullif(p.cause_delay_min, 0)          as raw_controllable_share,

        (p.on_time_flights + {{ k }} * pr.p_on_time) / (p.flights + {{ k }})         as adj_on_time_rate,
        (p.cancelled_flights + {{ k }} * pr.p_cancel) / (p.flights + {{ k }})        as adj_cancellation_rate,
        (p.total_arr_delay_min + {{ k }} * pr.mu_delay) / (p.completed_flights + {{ k }}) as adj_avg_arr_delay_min,
        (p.controllable_delay_min + {{ k }} * pr.cause_min_per_flight * pr.p_controllable)
            / nullif(p.cause_delay_min + {{ k }} * pr.cause_min_per_flight, 0)       as adj_controllable_share,

        -- alternative small-sample method kept for comparison: Wilson 95% lower bound
        (  (p.on_time_flights::numeric / p.flights) + 1.9208 / p.flights
         - 1.96 * sqrt(  (p.on_time_flights::numeric / p.flights)
                         * (1 - p.on_time_flights::numeric / p.flights) / p.flights
                       + 0.9604 / (p.flights::numeric * p.flights)))
        / (1 + 3.8416 / p.flights)                                                 as wilson_low_on_time_rate
    from pairs as p
    cross join priors as pr
    where p.flights >= {{ var('scorecard_min_flights') }}
),

standardised as (
    select
        a.*,
        (adj_on_time_rate       - avg(adj_on_time_rate)       over ()) / nullif(stddev_pop(adj_on_time_rate)       over (), 0) as z_on_time,
        (adj_cancellation_rate  - avg(adj_cancellation_rate)  over ()) / nullif(stddev_pop(adj_cancellation_rate)  over (), 0) as z_cancel,
        (adj_avg_arr_delay_min  - avg(adj_avg_arr_delay_min)  over ()) / nullif(stddev_pop(adj_avg_arr_delay_min)  over (), 0) as z_delay,
        (adj_controllable_share - avg(adj_controllable_share) over ()) / nullif(stddev_pop(adj_controllable_share) over (), 0) as z_controllable
    from adjusted as a
),

scored as (
    select
        s.*,
        -- low on-time is bad, so its z-score enters with a minus sign
          {{ var('weight_on_time') }}     * -coalesce(z_on_time, 0)
        + {{ var('weight_cancel') }}      *  coalesce(z_cancel, 0)
        + {{ var('weight_delay') }}       *  coalesce(z_delay, 0)
        + {{ var('weight_controllable') }} * coalesce(z_controllable, 0)                as risk_score
    from standardised as s
)

select
    sc.carrier_code,
    c.carrier_name,
    sc.airport_code,
    a.city_name,
    a.is_hub,
    w.first_ym                                                      as window_first_month,
    w.latest_ym                                                     as window_last_month,
    sc.flights,
    sc.completed_flights,
    round(sc.raw_on_time_rate, 4)                                   as raw_on_time_rate,
    round(sc.adj_on_time_rate, 4)                                   as adj_on_time_rate,
    round(sc.wilson_low_on_time_rate, 4)                            as wilson_low_on_time_rate,
    round(sc.raw_cancellation_rate, 4)                              as raw_cancellation_rate,
    round(sc.adj_cancellation_rate, 4)                              as adj_cancellation_rate,
    round(sc.raw_avg_arr_delay_min, 2)                              as raw_avg_arr_delay_min,
    round(sc.adj_avg_arr_delay_min, 2)                              as adj_avg_arr_delay_min,
    round(sc.raw_controllable_share, 4)                             as raw_controllable_share,
    round(sc.adj_controllable_share, 4)                             as adj_controllable_share,
    round(sc.z_on_time, 3)                                          as z_on_time,
    round(sc.z_cancel, 3)                                           as z_cancel,
    round(sc.z_delay, 3)                                            as z_delay,
    round(sc.z_controllable, 3)                                     as z_controllable,
    round(sc.risk_score, 4)                                         as risk_score,
    rank() over (order by sc.risk_score desc)                       as risk_rank,
    rank() over (order by sc.risk_score desc) <= {{ var('scorecard_priority_n') }} as is_priority
from scored as sc
cross join window_bounds as w
join {{ ref('dim_carrier') }} as c on c.carrier_code = sc.carrier_code
join {{ ref('dim_airport') }} as a on a.airport_code = sc.airport_code
