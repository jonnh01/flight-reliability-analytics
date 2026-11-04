"""Flight Operations Reliability - public dashboard.

Run locally:   streamlit run app/streamlit_app.py
Deployed on Streamlit Community Cloud from this same file. It reads only the small
Parquet files in data/marts/, so no database is needed in the cloud.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data  # noqa: E402

st.set_page_config(page_title="Flight Reliability Analytics", page_icon="✈️", layout="wide")

if not data.data_available():
    st.title("Flight Operations Reliability Analytics")
    st.warning(
        "No data yet. Run the pipeline first:\n\n"
        "`python -m pipeline.ingest` → `dbt build` → `python -m pipeline.export`"
    )
    st.stop()

manifest = data.load_manifest()
if manifest.get("synthetic_data"):
    st.error("⚠️ Showing SYNTHETIC test data. These numbers are made up - not real flights.")

with st.sidebar:
    st.markdown("### ✈️ Flight Reliability")
    st.caption(
        f"U.S. domestic flights, {data.month_label(manifest['first_month'])} – "
        f"{data.month_label(manifest['latest_month'])} · {manifest['total_flights']:,} flights. "
        "Source: U.S. Bureau of Transportation Statistics. Refreshed monthly; BTS publishes "
        "about two months after each month ends."
    )

pages = [
    st.Page("views/overview.py", title="Executive overview", icon="📊", default=True),
    st.Page("views/carriers_airports.py", title="Airlines & airports", icon="🛫"),
    st.Page("views/delay_causes.py", title="Delay causes & trends", icon="⏱️"),
    st.Page("views/scorecard.py", title="Reliability scorecard", icon="🎯"),
    st.Page("views/findings.py", title="Findings & what-if", icon="🧪"),
]
st.navigation(pages).run()
