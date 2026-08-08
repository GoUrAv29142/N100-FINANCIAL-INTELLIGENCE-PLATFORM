"""
Nifty 100 Financial Intelligence Platform — Streamlit Dashboard
Main entry point. Run with:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon=" ",
)

st.sidebar.title(" Nifty 100 Analytics")
st.sidebar.caption("Financial Intelligence Platform · 92 companies")
st.sidebar.markdown("---")

st.sidebar.markdown(
    """
Use the navigation menu above (or the links below) to move between
screens:

-  **Home** — universe overview & KPIs
-  **Company Profile** — deep dive on one ticker
-  **Screener** — multi-metric filtering
-  **Peer Comparison** — radar & benchmark view
-  **Trend Analysis** — multi-year, multi-metric overlay
-  **Sector Analysis** — bubble chart & sector medians
-  **Capital Allocation Map** — treemap of cash-use patterns
-  **Annual Reports** — BSE filing links
"""
)

st.sidebar.markdown("---")
st.sidebar.caption("Data: FY2011–2024 · Valuation: CY2019–2024 (simulated)")

st.title("Nifty 100 Financial Intelligence Platform")
st.write(
    "Select a screen from the **sidebar** (Streamlit automatically lists every "
    "file in `pages/`) to begin. Start with **Home** for a universe overview, "
    "or jump straight to the **Screener** to filter for investment candidates."
)

try:
    from utils.db import get_companies
    df = get_companies()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Companies Tracked", len(df))
    c2.metric("Sectors", df["broad_sector"].nunique())
    c3.metric("Latest Data Year", df["year"].max() if "year" in df.columns else "—")
    c4.metric("Avg ROE", f"{df['return_on_equity_pct'].mean():.1f}%" if "return_on_equity_pct" in df.columns else "—")
except Exception as e:
    st.warning(f"Could not load database preview: {e}")
    st.info("Make sure `data/nifty100.db` exists relative to this app.")