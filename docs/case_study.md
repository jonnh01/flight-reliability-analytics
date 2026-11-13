# Case studies

Two problems the data shows clearly, written up the way an operations or network-planning team would want them.

- **Data:** 12 months of BTS on-time data (Sep 2025 – Aug 2026), 7,049,869 scheduled flights.
- **Source of every number:** `analysis/case_studies.py`. The full tables are in [case_study_data.md](case_study_data.md) and are regenerated on every analysis run, so the evidence can be re-checked after each refresh. Section labels (A1, B2, …) point to those tables.
- **On-time:** the flight was completed and arrived less than 15 minutes late, counted out of **all scheduled flights**. See [metric_definitions.md](metric_definitions.md).

---

## Case study A: Why are flights into San Francisco so late?

### The problem

Flights **arriving at SFO** were on time **65.4%** of the time, against **74.3%** for flights **departing SFO**. That is a 9-point gap at the same airport over the same 12 months (A1). No other large western airport shows anything like it.

| Airport | On time, arriving | On time, departing | Air-traffic-system (NAS) share of arrival delay minutes |
|---|---:|---:|---:|
| **SFO** | **65.4%** | **74.3%** | **47.9%** |
| SAN | 71.0% | 75.0% | 30.6% |
| LAS | 76.8% | 75.9% | 21.8% |
| DEN | 78.1% | 75.8% | 27.8% |
| PHX | 78.5% | 77.0% | 13.4% |
| LAX | 78.6% | 78.5% | 16.0% |
| SEA | 78.6% | 78.5% | 21.7% |

NAS stands for the National Aviation System: air traffic control, airport capacity and heavy traffic. At SFO almost half of arrival delay minutes are NAS-coded, against 13–31% at its peers. **The delay is coming from the airport's capacity, not from the airlines.**

### The evidence

**1. It is not one airline.** Seven of the eight carriers with 1,000+ SFO arrivals do worse arriving at SFO than on their other arrivals (A4 vs A5):

| Carrier | On time into SFO | On time, all other arrivals | Gap |
|---|---:|---:|---:|
| Southwest (WN) | 49.9% | 75.0% | −25.1 pts |
| Alaska (AS) | 63.3% | 79.1% | −15.8 pts |
| Delta (DL) | 64.1% | 79.7% | −15.6 pts |
| Frontier (F9) | 56.3% | 71.3% | −15.0 pts |
| SkyWest (OO) | 63.1% | 77.6% | −14.5 pts |
| American (AA) | 63.6% | 73.0% | −9.4 pts |
| United (UA) | 70.2% | 78.4% | −8.2 pts |
| JetBlue (B6) | 69.3% | 68.5% | +0.8 pts |

**2. It started in April 2026.** On-time arrivals at SFO were 68.6–82.1% each month through March 2026. They then fell to **59.3%** in April and **48.3%** in June, and the NAS share of delay minutes jumped to 58.7–63.7% (A2):

| Month | Arrivals | On time | Avg arrival delay (min) | NAS share of delay min |
|---|---:|---:|---:|---:|
| Mar 2026 | 12,174 | 82.1% | −1.3 | 16.3% |
| **Apr 2026** | 12,413 | **59.3%** | 19.8 | **58.7%** |
| May 2026 | 13,147 | 53.3% | 25.2 | 63.7% |
| Jun 2026 | 13,452 | 48.3% | 29.8 | 55.3% |
| Jul 2026 | 13,874 | 51.9% | 27.0 | 49.4% |
| Aug 2026 | 13,579 | 56.8% | 22.7 | 45.8% |

That timing matches two published changes:

- **Runway repaving:** a runway repaving project ran **March 30 – October 2, 2026** ([KTVU](https://www.ktvu.com/news/sfo-arrivals-could-see-up-25-flights-delayed-due-repaving-project-upgrades)).
- **Arrival-rate cut:** an FAA rule change ended side-by-side approaches in clear weather. The two changes together cut SFO's arrival rate from about **54 to 36 arrivals an hour** ([ABC7/AP](https://abc7news.com/post/san-francisco-international-airport-faces-major-delays-faa-reduces-arrivals-runway-work-safety-issues/18819113/), [The Points Guy](https://thepointsguy.com/news/san-francisco-sfo-airport-faa-reduces-landing-rate)).

The data can't prove the cause on its own. But the break lands in the same month, it hits every airline, and it shows up as NAS (capacity) delay. That is exactly what a cut in arrival capacity would look like.

**3. Mid-day and late-evening arrivals suffer most** (A3):

- Arrivals scheduled for 6–7 a.m. were on time **91.0%** of the time.
- Arrivals scheduled 9 a.m. – 1 p.m. were on time **63–68%**.
- Arrivals scheduled 8–10 p.m. were on time **53–57%**.

In those windows NAS causes account for 55–59% of delay minutes, consistent with demand piling up against a capped arrival rate.

**4. Short West Coast feeder routes are hit hardest** (A6). The worst routes into SFO with 2,000+ flights are all short hops: Las Vegas (57.5%), San Diego (58.4%), Burbank (58.5%), Seattle (59.1%), Palm Springs (59.5%) and Los Angeles (59.7%). On most of these, NAS causes make up 52–60% of delay minutes. Short flights are the ones air traffic control typically holds on the ground at the origin when the destination is capped.

### What it means

- **For airlines:** schedules into SFO built for a ~54-per-hour airport ran against a ~36-per-hour reality from April 2026. Re-timing arrival banks away from 9 a.m. – 1 p.m. and 8–10 p.m., adding block time, and protecting connections at SFO would cut the knock-on delay that late arrivals cause (see the cascade finding in the README).
- **For travellers:** early-morning arrivals into SFO were by far the most reliable.
- **For this project:** the runway was due to reopen on October 2, 2026. The next monthly refreshes will show whether SFO arrivals recover, or whether the permanent end of side-by-side approaches keeps them low. That's a good thing to check after each refresh.

### Limits

- Delay causes are reported by the airlines. NAS is a broad category.
- The data covers through August 2026, so it can't yet show what happened after the runway reopened.
- The news sources describe the plan as announced at the end of March 2026. The data shows the effect but not the exact daily arrival rate.

---

## Case study B: Why does PSA Airlines dominate the priority list?

### The problem

PSA Airlines (OH) is a regional carrier that flies as American Eagle. It has **9 of the 20** carrier-airport pairs on the reliability scorecard's priority list, more than any other carrier (B6). Frontier and Allegiant come next with 3 each. Delta, United, Alaska and American have none.

| | PSA (OH) | All other carriers |
|---|---:|---:|
| Scheduled flights | 242,979 | 6,806,890 |
| On time | **69.7%** | 75.8% |
| Cancelled | **4.8%** | 1.8% |
| Avg arrival delay (completed flights) | 16.0 min | 8.2 min |
| Late-arriving-aircraft share of delay minutes | 49.1% | 39.4% |

### The evidence

**1. Cancellations, not just delays.** PSA cancels **2.7×** as often as the rest of the network (4.8% vs 1.8%, B1). The cancellation reason codes are surprising (B2):

| Cancellation reason (share of cancellations) | PSA | All others |
|---|---:|---:|
| Weather | **78.3%** | 59.2% |
| Carrier-caused | 9.6% | 23.3% |
| National Aviation System | 11.7% | 17.4% |

Most PSA cancellations are coded as weather. Weather hits all airlines at an airport, yet PSA cancels far more of its flights. A common explanation in the industry is that when weather cuts an airport's capacity, the regional (smaller-aircraft) flights are cancelled first to protect mainline flights. That is a hypothesis this data can't confirm, but it fits the pattern.

**2. The gap opens in bad-weather and peak months** (B3). In September and October 2025 PSA matched the network (82.9% vs 82.8% on time). In January 2026 PSA cancelled **11.6%** of flights against 4.5% for others. In June–August 2026 it cancelled **6.6–8.5%** against 1.5–2.5%.

**3. Washington National is the problem station** (B4). Washington National (DCA) is PSA's busiest airport (40,071 departures), and there PSA was on time **61.5%** of the time against **72.1%** for other carriers, with **6.4%** cancelled against 3.0%. At Charlotte (CLT), its second-biggest station, PSA is close to the others: 73.0% vs 74.7%.

**4. Delays spread further on PSA.** When the previous flight on the same aircraft landed 15+ minutes late, the next PSA flight arrived late **70.5%** of the time, against **66.4%** for other carriers. After an on-time previous flight the two are the same, 14.9% vs 14.8% (B5). So PSA's difficulty is recovering once something goes wrong, not starting the day badly.

### What it means

- **Where to look first:** for an operations team, the scorecard points at DCA and at PSA's irregular-operations recovery.
- **Weather cancellations:** spare aircraft or crews at DCA, or longer turn times on the first legs after a disruption, are the levers.
- **Separating regional from mainline:** the scorecard is doing its job here. Without it, PSA's problems would be hidden inside American's numbers.

### Limits

- Cancellation codes and delay causes are self-reported by airlines.
- The data has no aircraft type, crew or passenger information, so it can't show *why* PSA flights are chosen for cancellation.
- 2.7× is a ratio of rates over 12 months. Individual months vary a lot (B3).
