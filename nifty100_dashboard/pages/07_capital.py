import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_capital_allocation, get_companies

st.set_page_config(page_title="Capital Allocation Map | Nifty 100 Analytics", layout="wide")
st.title(" Capital Allocation Map")

st.caption(
    "Classifies each company's latest cash-flow year into one of 8 patterns "
    "based on the sign of Cash from Operations (CFO), Investing (CFI), and "
    "Financing (CFF) activities."
)

alloc = get_capital_allocation()
companies = get_companies()[["id", "company_name", "broad_sector"]].rename(columns={"id": "company_id"})
alloc = alloc.merge(companies, on="company_id", how="left")

if alloc.empty:
    st.info("No cash flow data available to build the capital allocation map.")
    st.stop()

pattern_counts = alloc.groupby("pattern_label")["company_id"].nunique().reset_index()
pattern_counts.columns = ["Pattern", "Companies"]

st.subheader("All 92 Companies by Capital Allocation Pattern")
fig = px.treemap(
    alloc, path=["pattern_label", "broad_sector", "company_id"],
    color="pattern_label",
)
fig.update_layout(height=560, margin=dict(t=20, b=20))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.subheader("Drill Down: Companies in a Pattern")
pattern_choice = st.selectbox("Pattern", options=sorted(alloc["pattern_label"].unique().tolist()))
subset = alloc[alloc["pattern_label"] == pattern_choice][
    ["company_id", "company_name", "broad_sector", "operating_activity", "investing_activity", "financing_activity", "year"]
]
st.dataframe(
    subset.rename(columns={
        "company_id": "Ticker", "company_name": "Company", "broad_sector": "Sector",
        "operating_activity": "CFO (₹Cr)", "investing_activity": "CFI (₹Cr)",
        "financing_activity": "CFF (₹Cr)", "year": "Year",
    }),
    hide_index=True, use_container_width=True,
)

csv = subset.to_csv(index=False).encode("utf-8")
st.download_button(" Download this pattern's companies as CSV", data=csv, file_name=f"{pattern_choice.replace(' ', '_')}.csv", mime="text/csv")