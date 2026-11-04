# Tableau Public dashboard (manual, about 3-4 hours)

Tableau Public cannot connect to your database or refresh on a schedule from local files, so it uses the CSV extracts. Re-publish after a refresh if you want it current; the Streamlit app is the always-fresh link.

## Data
After `python -m pipeline.export`, use the files in `data/tableau/`:
- `mart_carrier_monthly.csv` (main source)
- `mart_reliability_scorecard.csv`
- `mart_delay_causes.csv`
- `dim_airport.csv` (join to `mart_delay_causes` on `airport_code`)

## Suggested layout (one dashboard, 1200 × 800)
1. **Top row: KPI tiles** (latest month): flights, on-time rate, cancellation rate, avg arrival delay.
2. **Trend line**: on-time rate by month, one line per carrier (highlight on hover).
3. **Delay cause bar**: share of delay minutes by cause, filterable by carrier.
4. **Scorecard table**: top 20 by `risk_rank`, with colour on `risk_score`.
5. **Filters**: carrier, month range. Set them to apply to all sheets.

## Calculated fields
Create these in Tableau (aggregate from counts, never average the pre-computed rates):

```
On-time rate          SUM([On Time Flights]) / SUM([Scheduled Flights])
Cancellation rate     SUM([Cancelled Flights]) / SUM([Scheduled Flights])
Month                 DATE(LEFT(STR([Year Month]),4) + "-" + RIGHT(STR([Year Month]),2) + "-01")
Controllable share    (SUM([Carrier Delay Min]) + SUM([Late Aircraft Delay Min])) /
                      (SUM([Carrier Delay Min]) + SUM([Late Aircraft Delay Min]) + SUM([Nas Delay Min])
                       + SUM([Weather Delay Min]) + SUM([Security Delay Min]))
```

## Check before publishing
- Pick one month and one carrier; compare the on-time rate with the Streamlit app. They must match.
- Title says the data source and date range.
- Publish: File → Save to Tableau Public. Put the link in the README and on your resume.
