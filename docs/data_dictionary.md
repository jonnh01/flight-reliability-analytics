# Data dictionary

Tables in the `marts` schema (built by dbt). Business definitions: [metric_definitions.md](metric_definitions.md). The browsable version with lineage: `make docs`.

## fct_flights

Grain: one row per scheduled flight.

| Column | Type |
|---|---|
| `flight_id` | text |
| `year_month` | integer |
| `flight_date` | date |
| `carrier_code` | text |
| `origin_airport_code` | text |
| `dest_airport_code` | text |
| `route_key` | text |
| `tail_number` | text |
| `flight_number` | integer |
| `scheduled_dep_at` | timestamp without time zone |
| `scheduled_arr_at` | timestamp without time zone |
| `dep_hour` | integer |
| `time_of_day` | text |
| `distance_miles` | integer |
| `distance_band` | text |
| `dep_delay_min` | integer |
| `arr_delay_min` | integer |
| `is_on_time` | boolean |
| `is_arr_delayed_15` | boolean |
| `is_significant_delay` | boolean |
| `is_cancelled` | boolean |
| `cancellation_code` | text |
| `is_diverted` | boolean |
| `is_completed` | boolean |
| `carrier_delay_min` | integer |
| `weather_delay_min` | integer |
| `nas_delay_min` | integer |
| `security_delay_min` | integer |
| `late_aircraft_delay_min` | integer |
| `airline_controllable_delay_min` | integer |
| `total_cause_delay_min` | integer |
| `leg_number_of_day` | bigint |
| `prev_leg_flight_id` | text |
| `prev_leg_arr_delay_min` | integer |
| `scheduled_turn_min` | numeric |
| `is_rotation_consistent` | boolean |
| `loaded_at` | timestamp with time zone |

## dim_date

Grain: one row per calendar day.

| Column | Type |
|---|---|
| `date_day` | date |
| `year` | integer |
| `quarter` | integer |
| `month` | integer |
| `year_month` | integer |
| `month_label` | text |
| `day_of_month` | integer |
| `day_of_week` | integer |
| `day_name` | text |
| `is_weekend` | boolean |
| `is_holiday` | boolean |
| `holiday_name` | text |

## dim_carrier

Grain: one row per airline code.

| Column | Type |
|---|---|
| `carrier_code` | text |
| `carrier_name` | text |
| `carrier_type` | text |
| `first_seen_month` | integer |
| `last_seen_month` | integer |
| `flights_loaded` | bigint |

## dim_airport

Grain: one row per airport.

| Column | Type |
|---|---|
| `airport_code` | text |
| `city_name` | text |
| `state` | text |
| `departures` | bigint |
| `departures_rank` | bigint |
| `is_hub` | boolean |

## dim_route

Grain: one row per origin-destination pair.

| Column | Type |
|---|---|
| `route_key` | text |
| `origin_airport_code` | text |
| `dest_airport_code` | text |
| `distance_miles` | integer |
| `distance_band` | text |
| `flights_loaded` | bigint |

## mart_airport_monthly

Grain: origin airport x month.

| Column | Type |
|---|---|
| `airport_code` | text |
| `city_name` | text |
| `state` | text |
| `is_hub` | boolean |
| `year_month` | integer |
| `scheduled_departures` | bigint |
| `cancelled_flights` | bigint |
| `on_time_rate` | numeric |
| `cancellation_rate` | numeric |
| `avg_dep_delay_min` | numeric |
| `avg_arr_delay_min` | numeric |
| `weather_delay_min` | bigint |
| `nas_delay_min` | bigint |
| `total_cause_delay_min` | bigint |

## mart_carrier_monthly

Grain: carrier x month.

| Column | Type |
|---|---|
| `carrier_code` | text |
| `carrier_name` | text |
| `year_month` | integer |
| `scheduled_flights` | bigint |
| `completed_flights` | bigint |
| `cancelled_flights` | bigint |
| `diverted_flights` | bigint |
| `on_time_flights` | bigint |
| `delayed_15_flights` | bigint |
| `delayed_60_flights` | bigint |
| `on_time_rate` | numeric |
| `cancellation_rate` | numeric |
| `delay_15_rate` | numeric |
| `avg_arr_delay_min` | numeric |
| `p90_arr_delay_min` | double precision |
| `carrier_delay_min` | bigint |
| `weather_delay_min` | bigint |
| `nas_delay_min` | bigint |
| `security_delay_min` | bigint |
| `late_aircraft_delay_min` | bigint |
| `controllable_delay_share` | numeric |

## mart_delay_by_hour

Grain: month x scheduled departure hour.

| Column | Type |
|---|---|
| `year_month` | integer |
| `dep_hour` | integer |
| `time_of_day` | text |
| `scheduled_flights` | bigint |
| `on_time_rate` | numeric |
| `avg_dep_delay_min` | numeric |
| `avg_arr_delay_min` | numeric |
| `delay_15_rate` | numeric |
| `late_aircraft_delay_min` | bigint |
| `total_cause_delay_min` | bigint |

## mart_delay_causes

Grain: carrier x origin airport x month.

| Column | Type |
|---|---|
| `carrier_code` | text |
| `airport_code` | text |
| `year_month` | integer |
| `delayed_15_flights` | bigint |
| `carrier_delay_min` | bigint |
| `weather_delay_min` | bigint |
| `nas_delay_min` | bigint |
| `security_delay_min` | bigint |
| `late_aircraft_delay_min` | bigint |
| `total_cause_delay_min` | bigint |

## mart_delay_propagation

Grain: carrier x previous-leg delay bucket x leg number.

| Column | Type |
|---|---|
| `carrier_code` | text |
| `prev_leg_bucket` | text |
| `leg_number_capped` | bigint |
| `flights` | bigint |
| `delayed_15_flights` | bigint |
| `delay_15_rate` | numeric |
| `avg_dep_delay_min` | numeric |

## mart_pipeline_status

Grain: one row.

| Column | Type |
|---|---|
| `first_month` | integer |
| `latest_month` | integer |
| `months_loaded` | bigint |
| `total_flights` | bigint |
| `carriers` | bigint |
| `origin_airports` | bigint |
| `last_loaded_at` | timestamp with time zone |
| `built_at` | timestamp with time zone |

## mart_reliability_scorecard

Grain: carrier x origin airport (trailing window).

| Column | Type |
|---|---|
| `carrier_code` | text |
| `carrier_name` | text |
| `airport_code` | text |
| `city_name` | text |
| `is_hub` | boolean |
| `window_first_month` | integer |
| `window_last_month` | integer |
| `flights` | bigint |
| `completed_flights` | bigint |
| `raw_on_time_rate` | numeric |
| `adj_on_time_rate` | numeric |
| `wilson_low_on_time_rate` | numeric |
| `raw_cancellation_rate` | numeric |
| `adj_cancellation_rate` | numeric |
| `raw_avg_arr_delay_min` | numeric |
| `adj_avg_arr_delay_min` | numeric |
| `raw_controllable_share` | numeric |
| `adj_controllable_share` | numeric |
| `z_on_time` | numeric |
| `z_cancel` | numeric |
| `z_delay` | numeric |
| `z_controllable` | numeric |
| `risk_score` | numeric |
| `risk_rank` | bigint |
| `is_priority` | boolean |

## mart_route_performance

Grain: one row per route.

| Column | Type |
|---|---|
| `route_key` | text |
| `origin_airport_code` | text |
| `dest_airport_code` | text |
| `distance_miles` | integer |
| `distance_band` | text |
| `scheduled_flights` | bigint |
| `on_time_rate` | numeric |
| `cancellation_rate` | numeric |
| `avg_arr_delay_min` | numeric |
| `months_active` | bigint |
| `months_below_network` | bigint |
| `share_months_below_network` | numeric |

## mart_whatif_delayed_flights

Grain: one row per 15+ min delayed flight, latest month.

| Column | Type |
|---|---|
| `flight_id` | text |
| `carrier_code` | text |
| `airport_code` | text |
| `time_of_day` | text |
| `arr_delay_min` | integer |
| `carrier_delay_min` | integer |
| `weather_delay_min` | integer |
| `nas_delay_min` | integer |
| `security_delay_min` | integer |
| `late_aircraft_delay_min` | integer |
