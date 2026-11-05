# Metric definitions

Every metric is defined once, in `dbt/models/intermediate/int_flights__enriched.sql`, and every mart reuses those flags. If a number here and a number in a chart disagree, the SQL is the source of truth: fix whichever is wrong.

## Flight status flags (per flight)

| Flag | Definition |
|---|---|
| `is_cancelled` | BTS `Cancelled = 1` |
| `is_diverted` | BTS `Diverted = 1` |
| `is_completed` | not cancelled and not diverted |
| `is_arr_delayed_15` | BTS `ArrDel15 = 1` (arrived 15+ minutes late). Null for cancelled/diverted flights |
| `is_on_time` | completed **and** arrival delay < 15 minutes. Cancelled and diverted flights count as **not** on time. A completed flight whose arrival delay BTS left blank uses BTS's 15-minute flag, and counts as not on time if that is blank too (`tests/assert_completed_flights_have_arrival_delay.sql` keeps count) |
| `is_significant_delay` | arrival delay of 60+ minutes |
| `airline_controllable_delay_min` | `CarrierDelay + LateAircraftDelay` minutes (flights 15+ late only) |
| `total_cause_delay_min` | sum of all five cause columns (flights 15+ late only) |
| `time_of_day` | from the **scheduled** departure hour: morning 05–11, afternoon 12–16, evening 17–21, night 22–04 |

## Rates

| Metric | Numerator | Denominator | Why this denominator |
|---|---|---|---|
| On-time rate | on-time flights | **all scheduled flights** | Cancelling a flight should never make a carrier look more reliable |
| Cancellation rate | cancelled flights | all scheduled flights | |
| 15-minute delay rate | flights arriving 15+ late | completed flights | Only completed flights have an arrival |
| Average arrival delay | sum of arrival delay minutes (early = negative) | completed flights | Cancelled flights have no arrival time |
| Controllable delay share | airline-controllable cause minutes | all cause minutes | Shares of attributed minutes only |

**Note:** the DOT's published on-time percentage uses a slightly different denominator (it reports cancellations separately). This project's stricter on-time rate will therefore be a little lower than DOT headline figures. Say so if asked.

## Delay causes (BTS definitions)

| Cause | Meaning |
|---|---|
| Carrier | within the airline's control: maintenance, crew, cleaning, baggage, fueling |
| Late-arriving aircraft | the same aircraft arrived late on its previous flight |
| NAS (National Aviation System) | air traffic control, heavy traffic, non-extreme weather handled by the system |
| Weather | extreme weather |
| Security | security breaches, screening lines |

Cause minutes exist only for flights that arrived 15+ minutes late. For all other flights they are blank (null), not zero.

## Reliability scorecard

Grain: one row per **carrier × origin airport** over the trailing `scorecard_months` (12) months. Pairs with fewer than `scorecard_min_flights` (100) flights are not ranked.

1. **Raw measures:** on-time rate, cancellation rate, average arrival delay, controllable delay share.
2. **Small-sample adjustment (shrinkage).** Each measure is blended with the network average as if `k = 300` average flights were added:

   `adjusted rate = (events + k × network rate) / (flights + k)`

   A pair with 120 flights moves most of the way toward average. A pair with 6,000 flights barely moves. This stops small samples from topping or bottoming the ranking by chance. (The Wilson 95% lower bound is also stored, as an alternative method for comparison.)
3. **Standardise:** each adjusted measure becomes a z-score across all ranked pairs.
4. **Combine:** `risk score = 0.40 × (−z on-time) + 0.20 × z cancel + 0.25 × z delay + 0.15 × z controllable`. Higher = less reliable.
5. **Rank:** rank 1 = highest risk. The top 20 form the priority list.

Weights and `k` live in `dbt/dbt_project.yml` (`vars`). `analysis/scorecard_sensitivity.py` measures how much the top 10 changes when they change.
