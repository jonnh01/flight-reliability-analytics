import altair as alt
import streamlit as st

import data

st.title("Delay causes & trends")
st.caption(
    "BTS assigns a flight's delay minutes to five causes, but only for flights that arrived "
    "15+ minutes late. Shares below are shares of those attributed minutes."
)


@st.cache_data
def load():
    return (data.load_table("mart_delay_causes"), data.load_table("mart_delay_by_hour"),
            data.load_table("mart_delay_propagation"), data.load_table("dim_carrier"))


causes, by_hour, propagation, carriers = load()
names = dict(zip(carriers.carrier_code, carriers.carrier_name))

carrier = st.selectbox("Airline", ["All airlines"] + sorted(names.values()))
subset = causes if carrier == "All airlines" else causes[causes.carrier_code.map(names) == carrier]

long = subset.groupby("year_month", as_index=False)[list(data.CAUSE_COLUMNS)].sum().melt(
    "year_month", var_name="cause", value_name="minutes")
long["cause"] = long.cause.map(data.CAUSE_COLUMNS)
long["month"] = data.month_start(long.year_month)
long["share"] = long.minutes / long.groupby("year_month").minutes.transform("sum")

left, right = st.columns([3, 2])
with left:
    st.subheader("Share of delay minutes by cause")
    st.altair_chart(
        alt.Chart(long).mark_area().encode(
            x=alt.X("yearmonth(month):T", title=None),
            y=alt.Y("share:Q", stack="normalize", axis=alt.Axis(format="%"), title=None),
            color=alt.Color("cause:N", title="Cause", sort=list(data.CAUSE_COLUMNS.values())),
            tooltip=["cause", alt.Tooltip("yearmonth(month):T", title="Month"),
                     alt.Tooltip("share:Q", format=".1%"), alt.Tooltip("minutes:Q", format=",")],
        ).properties(height=320),
        width="stretch",
    )
with right:
    st.subheader("Whole period")
    whole = long.groupby("cause", as_index=False).minutes.sum()
    whole["share"] = whole.minutes / whole.minutes.sum()
    st.dataframe(whole.sort_values("share", ascending=False), hide_index=True, width="stretch",
                 column_config={"share": st.column_config.NumberColumn("Share", format="percent"),
                                "minutes": st.column_config.NumberColumn("Minutes", format="localized")})

st.subheader("Delays build through the day")
hourly = (by_hour.assign(delayed=by_hour.delay_15_rate * by_hour.scheduled_flights)
          .groupby("dep_hour", as_index=False)
          .agg(flights=("scheduled_flights", "sum"), delayed=("delayed", "sum")))
hourly["delay_15_rate"] = hourly.delayed / hourly.flights
st.altair_chart(
    alt.Chart(hourly).mark_bar().encode(
        x=alt.X("dep_hour:O", title="Scheduled departure hour (local)"),
        y=alt.Y("delay_15_rate:Q", axis=alt.Axis(format="%"), title="Share arriving 15+ min late"),
        tooltip=["dep_hour", alt.Tooltip("delay_15_rate:Q", format=".1%"), alt.Tooltip("flights:Q", format=",")],
    ).properties(height=280),
    width="stretch",
)

st.subheader("Cascade: a late aircraft makes the next flight late")
prop = propagation.groupby("prev_leg_bucket", as_index=False)[["flights", "delayed_15_flights"]].sum()
prop["delay_15_rate"] = prop.delayed_15_flights / prop.flights
prop["bucket"] = prop.prev_leg_bucket.str.split(": ").str[1]
st.altair_chart(
    alt.Chart(prop).mark_bar().encode(
        x=alt.X("bucket:N", sort=list(prop.sort_values("prev_leg_bucket").bucket), title="Same aircraft's previous flight"),
        y=alt.Y("delay_15_rate:Q", axis=alt.Axis(format="%"), title="Share of flights 15+ min late"),
        tooltip=["bucket", alt.Tooltip("delay_15_rate:Q", format=".1%"), alt.Tooltip("flights:Q", format=",")],
    ).properties(height=280),
    width="stretch",
)
st.caption("Built with a SQL window function (LAG over each tail number's flights that day). "
           "Shows association: a late inbound aircraft is one cause, but shared factors like weather also play a part.")
