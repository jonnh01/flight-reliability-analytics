# Data quality notes (fill in from the real data)

Profile each new month with these queries, then write what you find in the table. These notes are good interview material.

```sql
-- row counts and blanks per month
select _year_month, count(*) as rows,
       count(*) filter (where tail_number is null) as missing_tail,
       count(*) filter (where cancelled::numeric = 1) as cancelled,
       count(*) filter (where arr_delay is null) as missing_arr_delay,
       count(*) filter (where carrier_delay is not null) as rows_with_causes
from raw.bts_flights group by 1 order by 1;

-- after dbt: flights whose previous leg did not land where they depart (tail-number issues)
select count(*) filter (where is_rotation_consistent = false) as broken_rotations,
       count(*) filter (where is_rotation_consistent) as good_rotations
from marts.fct_flights;

-- cause minutes that do not add up to the arrival delay
select count(*) from marts.fct_flights
where is_arr_delayed_15 and abs(total_cause_delay_min - arr_delay_min) > 1;

-- carriers not in the seed lookup
select * from marts.dim_carrier where carrier_type = 'unknown';
```

| Check | What I found | Rule applied |
|---|---|---|
| Missing tail numbers | _x% of rows, mostly cancelled flights_ | Excluded from rotation analysis only |
| Cancelled flights without arrival | _expected_ | Count in reliability, exclude from delay averages |
| Cause columns blank for <15 min delays | _expected (BTS rule)_ | Kept as null, not 0 |
| `2400` times | _n rows_ | Parsed as midnight at the end of the day |
| FlightDate format | _ISO or M/D/YYYY?_ | Staging accepts both |
| Unknown carrier codes | _list_ | Added to `dbt/seeds/carriers.csv` |
| Duplicate flight identities | _n_ | _rule_ |
