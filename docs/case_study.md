# Operational case study (template: fill with REAL findings only)

Pick **one** concrete problem the data shows, e.g. a hub whose evening on-time rate collapses mainly through late-arriving aircraft. One page. Every number from your own queries.

## 1. Problem
_One sentence: which carrier/airport/time window, and how far below the network it is._

## 2. Evidence
_2-4 numbers with their source (mart or query), e.g. on-time rate vs network, share of delay minutes by cause, how the delay rate rises through the day._

Starter queries:

```sql
-- candidates: priority pairs from the scorecard
select risk_rank, carrier_name, airport_code, flights, raw_on_time_rate, raw_controllable_share
from marts.mart_reliability_scorecard where is_priority order by risk_rank;

-- one pair's delay causes by month
select year_month, carrier_delay_min, late_aircraft_delay_min, nas_delay_min, weather_delay_min
from marts.mart_delay_causes
where carrier_code = 'XX' and airport_code = 'YYY' order by year_month;

-- cascade: delay rate by leg of the day for that carrier
select prev_leg_bucket, leg_number_capped, flights, delay_15_rate
from marts.mart_delay_propagation where carrier_code = 'XX' order by 1, 2;
```

## 3. Likely causes
_What the evidence points to, and what else could explain it (weather days, congestion, schedule design)._

## 4. What we can and cannot conclude
_Association vs cause. Data limits (self-reported causes, local times, no crew or maintenance data)._

## 5. Recommendation
_One or two actions an operations team could test (e.g. larger turn buffers on the first evening rotation at that hub), and how to measure whether they worked._
