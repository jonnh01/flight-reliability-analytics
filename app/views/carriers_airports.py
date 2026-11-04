import altair as alt
import streamlit as st

import data

st.title("Airlines & airports")


@st.cache_data
def load():
    return (data.load_table("mart_carrier_monthly"), data.load_table("mart_airport_monthly"),
            data.load_table("mart_route_performance"))


carrier_monthly, airport_monthly, routes = load()
months = sorted(carrier_monthly.year_month.unique())
labels = {data.month_label(m): m for m in months}
start_label, end_label = st.select_slider("Months", options=list(labels), value=(list(labels)[0], list(labels)[-1]))
lo, hi = labels[start_label], labels[end_label]

tab_carriers, tab_airports, tab_routes = st.tabs(["Airlines", "Airports", "Routes"])

with tab_carriers:
    cm = carrier_monthly[carrier_monthly.year_month.between(lo, hi)].copy()
    chosen = st.multiselect("Airlines", sorted(cm.carrier_name.unique()), default=sorted(cm.carrier_name.unique())[:5])
    cm["month"] = data.month_start(cm.year_month)
    st.altair_chart(
        alt.Chart(cm[cm.carrier_name.isin(chosen)]).mark_line(point=True).encode(
            x=alt.X("yearmonth(month):T", title=None),
            y=alt.Y("on_time_rate:Q", axis=alt.Axis(format="%"), scale=alt.Scale(zero=False), title="On-time rate"),
            color=alt.Color("carrier_name:N", title="Airline"),
            tooltip=["carrier_name", alt.Tooltip("yearmonth(month):T", title="Month"),
                     alt.Tooltip("on_time_rate:Q", format=".1%"), alt.Tooltip("scheduled_flights:Q", format=",")],
        ).properties(height=340),
        width="stretch",
    )
    totals = cm.groupby("carrier_name", as_index=False)[["scheduled_flights", "on_time_flights", "cancelled_flights"]].sum()
    totals["on_time_rate"] = totals.on_time_flights / totals.scheduled_flights
    totals["cancellation_rate"] = totals.cancelled_flights / totals.scheduled_flights
    st.dataframe(
        totals.sort_values("on_time_rate")[["carrier_name", "scheduled_flights", "on_time_rate", "cancellation_rate"]],
        column_config={"on_time_rate": st.column_config.NumberColumn("On-time", format="percent"),
                       "cancellation_rate": st.column_config.NumberColumn("Cancelled", format="percent"),
                       "scheduled_flights": st.column_config.NumberColumn("Flights", format="localized"),
                       "carrier_name": "Airline"},
        hide_index=True, width="stretch",
    )

with tab_airports:
    am = airport_monthly[airport_monthly.year_month.between(lo, hi)].copy()
    am["on_time_flights"] = am.on_time_rate * am.scheduled_departures
    min_departures = st.slider("Minimum departures in period", 0, int(am.groupby("airport_code").scheduled_departures.sum().max()), 1000, step=500)
    totals = am.groupby(["airport_code", "city_name", "is_hub"], as_index=False).agg(
        departures=("scheduled_departures", "sum"), cancelled=("cancelled_flights", "sum"),
        on_time=("on_time_flights", "sum"),
    )
    totals["on_time_rate"] = totals.on_time / totals.departures
    totals["cancellation_rate"] = totals.cancelled / totals.departures
    totals = totals[totals.departures >= min_departures]
    st.altair_chart(
        alt.Chart(totals).mark_circle().encode(
            x=alt.X("departures:Q", scale=alt.Scale(type="log"), title="Departures (log scale)"),
            y=alt.Y("on_time_rate:Q", axis=alt.Axis(format="%"), scale=alt.Scale(zero=False), title="On-time rate"),
            size=alt.Size("departures:Q", legend=None),
            color=alt.Color("is_hub:N", title="Hub"),
            tooltip=["airport_code", "city_name", alt.Tooltip("departures:Q", format=","),
                     alt.Tooltip("on_time_rate:Q", format=".1%"), alt.Tooltip("cancellation_rate:Q", format=".2%")],
        ).properties(height=380),
        width="stretch",
    )
    st.caption("Each dot is an airport (departures only). Bigger airports sit to the right.")

with tab_routes:
    min_flights = st.number_input("Minimum flights on the route", value=200, step=100)
    worst = routes[routes.scheduled_flights >= min_flights].sort_values(
        ["share_months_below_network", "on_time_rate"], ascending=[False, True]).head(25)
    st.markdown("**Routes that most persistently underperform the network** (share of months below the network on-time rate)")
    st.dataframe(
        worst[["route_key", "scheduled_flights", "on_time_rate", "avg_arr_delay_min", "months_below_network", "months_active"]],
        column_config={"on_time_rate": st.column_config.NumberColumn("On-time", format="percent"),
                       "route_key": "Route", "scheduled_flights": "Flights",
                       "avg_arr_delay_min": st.column_config.NumberColumn("Avg arr delay (min)", format="%.1f"),
                       "months_below_network": "Months below network", "months_active": "Months flown"},
        hide_index=True, width="stretch",
    )
