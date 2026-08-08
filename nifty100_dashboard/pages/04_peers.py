import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_peer_groups_list, get_peers

st.set_page_config(page_title="Peer Comparison | Nifty 100 Analytics", layout="wide")
st.title(" Peer Comparison")

groups = get_peer_groups_list()
group_name = st.selectbox("Peer group", options=groups)

peers = get_peers(group_name)
if peers.empty:
    st.warning("No peer data found for this group.")
    st.stop()

RADAR_METRICS = {
    "return_on_equity_pct": "ROE %",
    "return_on_capital_employed_pct": "ROCE %",
    "net_profit_margin_pct": "NPM %",
    "operating_profit_margin_pct": "OPM %",
    "revenue_cagr_5yr": "Rev CAGR 5yr %",
    "pat_cagr_5yr": "PAT CAGR 5yr %",
    "asset_turnover": "Asset Turnover",
    "interest_coverage": "Interest Coverage",
}
metrics_available = [m for m in RADAR_METRICS if m in peers.columns]

company_choice = st.selectbox(
    "Company to highlight",
    options=peers["company_id"].tolist(),
    format_func=lambda t: f"{t} — {peers.loc[peers['company_id']==t, 'company_name'].values[0]}"
                           if not peers.loc[peers['company_id']==t].empty else t,
)

st.subheader(f"{company_choice} vs {group_name} Average")

company_row = peers[peers["company_id"] == company_choice]
avg_values = peers[metrics_available].mean(numeric_only=True)

if not company_row.empty:
    company_vals = company_row[metrics_available].iloc[0].fillna(0).tolist()
    avg_vals = avg_values.fillna(0).tolist()
    labels = [RADAR_METRICS[m] for m in metrics_available]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=company_vals, theta=labels, fill="toself", name=company_choice))
    fig.add_trace(go.Scatterpolar(r=avg_vals, theta=labels, fill="toself", name=f"{group_name} Avg", opacity=0.6))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), height=500, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Selected company has no ratio data for the latest year.")

st.markdown("---")

st.subheader("Side-by-Side Comparison")
table_cols = ["company_id", "company_name", "is_benchmark"] + metrics_available
table_cols = [c for c in table_cols if c in peers.columns]
display = peers[table_cols].rename(columns={"company_id": "Ticker", "company_name": "Company", "is_benchmark": "Benchmark"})
display = display.rename(columns=RADAR_METRICS)


def highlight_benchmark(row):
    is_bench = row.get("Benchmark", 0) == 1
    return ["background-color: #FFF3CD" if is_bench else "" for _ in row]

st.dataframe(display.style.apply(highlight_benchmark, axis=1), hide_index=True, use_container_width=True)