import altair as alt
import streamlit as st

import data

st.title("Reliability scorecard")


@st.cache_data
def load():
    return data.load_table("mart_reliability_scorecard")


sc = load()
st.caption(
    f"Every airline at every airport with enough flights, ranked by a volume-adjusted risk score "
    f"({data.month_label(sc.window_first_month.iloc[0])} – {data.month_label(sc.window_last_month.iloc[0])}). "
    "Rank 1 = the combination operations should look at first."
)

with st.expander("How the score works"):
    st.markdown(
        """
- **Four measures:** on-time rate, cancellation rate, average arrival delay, and the share of
  delay minutes the airline controls (its own delays + late-arriving aircraft).
- **Small-sample adjustment:** each rate is blended with the network average, weighted as if
  300 average flights were added. Pairs with few flights move toward average, so luck cannot
  put them at the top or bottom. Pairs with thousands of flights barely move.
- **Score:** each adjusted measure becomes a z-score (distance from average), then they are
  combined with weights 40% on-time, 20% cancellations, 25% delay, 15% controllable share.
- **Robustness:** `docs/scorecard_sensitivity.md` shows how much the top 10 changes under
  other weights or methods.
"""
    )

col1, col2 = st.columns(2)
carrier = col1.selectbox("Airline", ["All"] + sorted(sc.carrier_name.unique()))
hubs_only = col2.toggle("Hub airports only")
view = sc.copy()
if carrier != "All":
    view = view[view.carrier_name == carrier]
if hubs_only:
    view = view[view.is_hub.astype(bool)]

st.subheader("Priority list")
top = view.sort_values("risk_rank").head(20)
st.dataframe(
    top[["risk_rank", "carrier_name", "airport_code", "city_name", "flights", "raw_on_time_rate",
         "adj_on_time_rate", "raw_cancellation_rate", "raw_avg_arr_delay_min", "raw_controllable_share", "risk_score"]],
    column_config={
        "risk_rank": "Rank", "carrier_name": "Airline", "airport_code": "Airport", "city_name": "City",
        "flights": st.column_config.NumberColumn("Flights", format="localized"),
        "raw_on_time_rate": st.column_config.NumberColumn("On-time (actual)", format="percent"),
        "adj_on_time_rate": st.column_config.NumberColumn("On-time (adjusted)", format="percent"),
        "raw_cancellation_rate": st.column_config.NumberColumn("Cancelled", format="percent"),
        "raw_avg_arr_delay_min": st.column_config.NumberColumn("Avg delay (min)", format="%.1f"),
        "raw_controllable_share": st.column_config.NumberColumn("Airline-controlled", format="percent"),
        "risk_score": st.column_config.ProgressColumn("Risk score", min_value=float(sc.risk_score.min()),
                                                       max_value=float(sc.risk_score.max()), format="%.2f"),
    },
    hide_index=True, width="stretch",
)

st.subheader("Why the adjustment matters")
st.altair_chart(
    alt.Chart(view).mark_circle(opacity=0.6).encode(
        x=alt.X("flights:Q", scale=alt.Scale(type="log"), title="Flights (log scale)"),
        y=alt.Y("raw_on_time_rate:Q", axis=alt.Axis(format="%"), title="Actual on-time rate"),
        color=alt.Color("is_priority:N", title="On priority list"),
        tooltip=["carrier_name", "airport_code", alt.Tooltip("flights:Q", format=","),
                 alt.Tooltip("raw_on_time_rate:Q", format=".1%"), alt.Tooltip("adj_on_time_rate:Q", format=".1%"),
                 "risk_rank"],
    ).properties(height=360),
    width="stretch",
)
st.caption("Small pairs (left) scatter widely by chance. The adjusted score does not let them dominate the list.")
