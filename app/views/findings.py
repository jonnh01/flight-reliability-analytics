import streamlit as st

import data

st.title("Findings & what-if")


@st.cache_data
def load():
    return data.load_table("mart_whatif_delayed_flights"), data.load_table("mart_carrier_monthly")


delayed, carrier_monthly = load()
latest = int(carrier_monthly.year_month.max())

st.subheader("Key findings")
# Write these from YOUR verified results (notebook + scorecard). Keep each one to a sentence
# with a number, and say what it does not prove. Until then, the placeholder below shows.
FINDINGS: list[str] = [
    "**Late planes make late planes.** When an aircraft's previous flight landed 15+ minutes late, "
    "65.9% of its next flights were late too, vs 15.2% after an on-time previous flight "
    "(risk ratio 4.33, 95% CI 4.29-4.37). An association, not proof of cause.",
    "**When you fly matters more than which airline.** Evening departures had 2.70x the odds of a "
    "15+ minute delay vs morning ones after controlling for carrier, month, distance and hubs; "
    "carrier differences are small by comparison (Cramer's V 0.072).",
    "**SFO arrivals collapsed in April 2026.** Flights into SFO were on time 82.1% in March but "
    "48-59% from April to August, with air-traffic-system delays up to 64% of delay minutes. That "
    "matches the FAA's arrival-rate cut during runway work (see docs/case_study.md).",
    "**PSA Airlines cancels 2.7x as often as the rest of the network** (4.8% vs 1.8%), mostly coded "
    "as weather, and holds 9 of the scorecard's 20 priority spots.",
]
# Numbers above: Sep 2025 - Aug 2026 data, from analysis/01_statistical_analysis.ipynb and
# docs/case_study_data.md. Update them when the analysis is re-run on newer data.
if FINDINGS:
    for item in FINDINGS:
        st.markdown(f"- {item}")
else:
    st.info("Findings will be added once the analysis on real BTS data is reviewed.")

st.divider()
st.subheader(f"What-if: shrink one cause of delay ({data.month_label(latest)})")
st.warning(
    "**Hypothetical scenario, not a forecast.** It assumes every delayed flight loses the same "
    "share of its minutes from the chosen causes, with no knock-on effects on later flights and "
    "no change to cancellations. Use it to compare which causes matter most, not to predict results."
)

c1, c2, c3 = st.columns(3)
r_late = c1.slider("Late-arriving aircraft delay cut by", 0, 100, 20, format="%d%%")
r_carrier = c2.slider("Carrier delay cut by", 0, 100, 0, format="%d%%")
r_nas = c3.slider("Air traffic (NAS) delay cut by", 0, 100, 0, format="%d%%")

month_totals = carrier_monthly[carrier_monthly.year_month == latest]
result = data.whatif_on_time(
    delayed,
    total_flights=int(month_totals.scheduled_flights.sum()),
    on_time_flights=int(month_totals.on_time_flights.sum()),
    reductions={"late_aircraft_delay_min": r_late / 100, "carrier_delay_min": r_carrier / 100,
                "nas_delay_min": r_nas / 100},
)
m1, m2, m3 = st.columns(3)
m1.metric("Actual on-time rate", f"{result['current_on_time_rate']:.1%}")
m2.metric("Scenario on-time rate", f"{result['scenario_on_time_rate']:.1%}",
          f"{(result['scenario_on_time_rate'] - result['current_on_time_rate']) * 100:+.1f} pts")
m3.metric("Flights moved under 15 min late", f"{result['recovered_flights']:,}")
st.caption(f"Delay minutes removed in the scenario: {result['minutes_saved']:,.0f}")
