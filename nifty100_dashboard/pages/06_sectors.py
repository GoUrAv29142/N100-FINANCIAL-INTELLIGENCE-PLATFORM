import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_companies, get_all_financial_ratios

st.set_page_config(page_title="Sector Analysis | Nifty 100 Analytics", layout="wide")
st.title(" Sector Analysis")

companies = get_companies()
ratios = get_all_financial_ratios()
latest_year = ratios["year"].max()
snap = ratios[ratios["year"] == latest_year].merge(
    companies[["id", "company_name", "broad_sector", "sub_sector"]].rename(columns={"id": "company_id"}),
    on="company_id", how="left",
)

sectors = sorted(snap["broad_sector"].dropna().unique().tolist())
sector_choice = st.selectbox("Sector", options=["All Sectors"] + sectors)

plot_df = snap if sector_choice == "All Sectors" else snap[snap["broad_sector"] == sector_choice]
plot_df = plot_df.dropna(subset=["sales", "return_on_equity_pct", "market_cap_crore"])

st.subheader(f"Revenue vs ROE — {sector_choice} ({latest_year})")
if not plot_df.empty:
    fig = px.scatter(
        plot_df, x="sales", y="return_on_equity_pct", size="market_cap_crore",
        color="sub_sector", hover_name="company_name",
        labels={"sales": "Revenue (₹Cr)", "return_on_equity_pct": "ROE (%)", "market_cap_crore": "Market Cap"},
        size_max=50,
    )
    fig.update_layout(height=500, margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough data (revenue / ROE / market cap) to plot this sector.")

st.markdown("---")

st.subheader("Sector Median KPIs")
sector_medians = snap.groupby("broad_sector")[
    ["return_on_equity_pct", "operating_profit_margin_pct", "debt_to_equity", "pe_ratio"]
].median(numeric_only=True).reset_index()

metric_for_bar = st.selectbox(
    "Metric", options=["return_on_equity_pct", "operating_profit_margin_pct", "debt_to_equity", "pe_ratio"],
    format_func=lambda m: {"return_on_equity_pct": "Median ROE %", "operating_profit_margin_pct": "Median OPM %",
                            "debt_to_equity": "Median D/E", "pe_ratio": "Median P/E"}[m],
)
fig2 = px.bar(sector_medians.sort_values(metric_for_bar, ascending=False), x="broad_sector", y=metric_for_bar)
fig2.update_layout(height=420, margin=dict(t=20, b=20), xaxis_title="Sector")
st.plotly_chart(fig2, use_container_width=True)