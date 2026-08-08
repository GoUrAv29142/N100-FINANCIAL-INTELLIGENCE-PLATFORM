import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_companies, get_ratios

st.set_page_config(page_title="Trend Analysis | Nifty 100 Analytics", layout="wide")
st.title(" Trend Analysis")

companies = get_companies()
search_options = (companies["id"] + " — " + companies["company_name"].astype(str).str.strip()).sort_values().tolist()

query = st.text_input("Search company", "")
filtered = [o for o in search_options if query.lower() in o.lower()] if query else search_options
if not filtered:
    st.warning("Ticker not found — please try another")
    st.stop()
selection = st.selectbox("Company", options=filtered)
ticker = selection.split(" — ")[0]

METRIC_OPTIONS = {
    "return_on_equity_pct": "ROE %",
    "return_on_capital_employed_pct": "ROCE %",
    "net_profit_margin_pct": "Net Profit Margin %",
    "operating_profit_margin_pct": "OPM %",
    "debt_to_equity": "Debt-to-Equity",
    "free_cash_flow_cr": "Free Cash Flow (₹Cr)",
    "revenue_cagr_5yr": "Revenue CAGR 5yr %",
    "pat_cagr_5yr": "PAT CAGR 5yr %",
    "pe_ratio": "P/E Ratio",
}

selected_metrics = st.multiselect(
    "Metrics to overlay (up to 3)", options=list(METRIC_OPTIONS.keys()),
    default=["return_on_equity_pct"], format_func=lambda m: METRIC_OPTIONS[m], max_selections=3,
)

hist = get_ratios(ticker).tail(10)
if hist.empty:
    st.info("No ratio history available for this company.")
    st.stop()

fig = go.Figure()
for m in selected_metrics:
    if m not in hist.columns:
        continue
    series = hist[["year", m]].dropna()
    fig.add_trace(go.Scatter(x=series["year"], y=series[m], mode="lines+markers", name=METRIC_OPTIONS[m]))

    vals = series[m].tolist()
    years = series["year"].tolist()
    for i in range(1, len(vals)):
        if vals[i - 1] not in (0, None) and pd.notna(vals[i - 1]) and pd.notna(vals[i]):
            yoy = (vals[i] - vals[i - 1]) / abs(vals[i - 1]) * 100
            fig.add_annotation(
                x=years[i], y=vals[i], text=f"{yoy:+.0f}%", showarrow=False,
                yshift=12, font=dict(size=9),
            )

fig.update_layout(height=500, margin=dict(t=30, b=20), title=f"{ticker} — 10-Year Trend")
st.plotly_chart(fig, use_container_width=True)

csv = hist.to_csv(index=False).encode("utf-8")
st.download_button("⬇ Download trend data as CSV", data=csv, file_name=f"{ticker}_trends.csv", mime="text/csv")