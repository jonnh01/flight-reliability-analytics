import altair as alt
import streamlit as st

import data

st.title("Executive overview")


@st.cache_data
def load():
    return data.load_table("mart_carrier_monthly"), data.load_manifest()


carrier_monthly, manifest = load()
latest = int(carrier_monthly.year_month.max())
months = sorted(carrier_monthly.year_month.unique())
previous = int(months[-2]) if len(months) > 1 else None

now, before = data.network_kpis(carrier_monthly, latest), (
    data.network_kpis(carrier_monthly, previous) if previous else None
)
st.caption(f"Latest month: **{data.month_label(latest)}**" + (f" (vs {data.month_label(previous)})" if previous else ""))


def delta(key, scale=100, unit=" pts"):
    return None if before is None else f"{(now[key] - before[key]) * scale:+.1f}{unit}"


c1, c2, c3, c4 = st.columns(4)
c1.metric("Flights scheduled", f"{now['flights']:,}", None if before is None else f"{now['flights'] - before['flights']:+,}")
c2.metric("On-time rate", f"{now['on_time_rate']:.1%}", delta("on_time_rate"))
c3.metric("Cancellation rate", f"{now['cancellation_rate']:.2%}", delta("cancellation_rate"), delta_color="inverse")
c4.metric("Avg arrival delay", f"{now['avg_arr_delay_min']:.1f} min",
          delta("avg_arr_delay_min", 1, " min"), delta_color="inverse")

st.subheader("On-time rate by month")
trend = carrier_monthly.groupby("year_month", as_index=False)[["on_time_flights", "scheduled_flights", "cancelled_flights"]].sum()
trend["on_time_rate"] = trend.on_time_flights / trend.scheduled_flights
trend["cancellation_rate"] = trend.cancelled_flights / trend.scheduled_flights
trend["month"] = data.month_start(trend.year_month)
st.altair_chart(
    alt.Chart(trend).mark_line(point=True).encode(
        x=alt.X("yearmonth(month):T", title=None),
        y=alt.Y("on_time_rate:Q", title="On-time rate", axis=alt.Axis(format="%"), scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("yearmonth(month):T", title="Month"),
                 alt.Tooltip("on_time_rate:Q", format=".1%", title="On-time"),
                 alt.Tooltip("scheduled_flights:Q", format=",", title="Flights")],
    ).properties(height=300),
    width="stretch",
)

st.subheader(f"Carriers in {data.month_label(latest)}")
latest_carriers = carrier_monthly[carrier_monthly.year_month == latest].sort_values("on_time_rate")
st.altair_chart(
    alt.Chart(latest_carriers).mark_bar().encode(
        x=alt.X("on_time_rate:Q", title="On-time rate", axis=alt.Axis(format="%")),
        y=alt.Y("carrier_name:N", sort="-x", title=None),
        tooltip=["carrier_name", alt.Tooltip("on_time_rate:Q", format=".1%"),
                 alt.Tooltip("scheduled_flights:Q", format=","),
                 alt.Tooltip("cancellation_rate:Q", format=".2%")],
    ).properties(height=28 * len(latest_carriers) + 20),
    width="stretch",
)
st.caption("On time = arrived less than 15 minutes late. Cancelled and diverted flights count as not on time.")
