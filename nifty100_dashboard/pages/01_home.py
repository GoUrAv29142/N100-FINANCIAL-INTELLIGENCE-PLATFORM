import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_companies, get_pl, get_ratios, get_pros_cons

st.set_page_config(page_title="Company Profile | Nifty 100 Analytics", layout="wide")
st.title(" Company Profile")

companies = get_companies()

search_options = (companies["id"] + " — " + companies["company_name"].astype(str).str.strip()).sort_values().tolist()
query = st.text_input("Search by company name or ticker", "")

filtered = [o for o in search_options if query.lower() in o.lower()] if query else search_options
if not filtered:
    st.warning("Ticker not found — please try another")
    st.stop()

selection = st.selectbox("Matching companies", options=filtered, index=0)
ticker = selection.split(" — ")[0]

row = companies[companies["id"] == ticker]
if row.empty:
    st.warning("Ticker not found — please try another")
    st.stop()
row = row.iloc[0]

st.markdown("---")
c1, c2 = st.columns([1, 3])
with c1:
    if pd.notna(row.get("company_logo")):
        try:
            st.image(row["company_logo"], width=120)
        except Exception:
            st.write("")
with c2:
    st.subheader(str(row["company_name"]).strip())
    st.caption(f"{row.get('broad_sector', '—')} · {row.get('sub_sector', '—')} · NSE: {ticker}")
    about = row.get("about_company")
    if pd.notna(about):
        st.write(about)

st.markdown("---")

st.subheader("Key Metrics (Latest Year)")
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("ROE", f"{row.get('return_on_equity_pct', float('nan')):.1f}%" if pd.notna(row.get("return_on_equity_pct")) else "N/A")
k2.metric("ROCE", f"{row.get('return_on_capital_employed_pct', float('nan')):.1f}%" if pd.notna(row.get("return_on_capital_employed_pct")) else "N/A")
k3.metric("Net Profit Margin", f"{row.get('net_profit_margin_pct', float('nan')):.1f}%" if pd.notna(row.get("net_profit_margin_pct")) else "N/A")
k4.metric("D/E", f"{row.get('debt_to_equity', float('nan')):.2f}" if pd.notna(row.get("debt_to_equity")) else "N/A")
k5.metric("Revenue CAGR (5yr)", f"{row.get('revenue_cagr_5yr', float('nan')):.1f}%" if pd.notna(row.get("revenue_cagr_5yr")) else "N/A")
k6.metric("FCF (latest, ₹Cr)", f"{row.get('free_cash_flow_cr', float('nan')):.0f}" if pd.notna(row.get("free_cash_flow_cr")) else "N/A")

st.markdown("---")

pl = get_pl(ticker)
if not pl.empty:
    pl_10 = pl.tail(10).copy()
    st.subheader("Revenue & Net Profit — Last 10 Years")
    fig = go.Figure()
    fig.add_bar(x=pl_10["year"], y=pl_10["sales"], name="Revenue (₹Cr)")
    fig.add_bar(x=pl_10["year"], y=pl_10["net_profit"], name="Net Profit (₹Cr)")
    fig.update_layout(barmode="group", height=420, margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No P&L history available for this company.")

ratios_hist = get_ratios(ticker).tail(10)
if not ratios_hist.empty and {"return_on_equity_pct", "return_on_capital_employed_pct"}.issubset(ratios_hist.columns):
    st.subheader("ROE vs ROCE — Last 10 Years")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=ratios_hist["year"], y=ratios_hist["return_on_equity_pct"], name="ROE %", mode="lines+markers"))
    fig2.add_trace(go.Scatter(x=ratios_hist["year"], y=ratios_hist["return_on_capital_employed_pct"], name="ROCE %", mode="lines+markers"))
    fig2.update_layout(height=380, margin=dict(t=20, b=20))
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Not enough ratio history for ROE/ROCE trend.")

st.markdown("---")

st.subheader("Pros & Cons")
pc = get_pros_cons(ticker)
pcol1, pcol2 = st.columns(2)
with pcol1:
    st.markdown("**Pros**")
    pros = pc["pros"].dropna().tolist() if not pc.empty else []
    if pros:
        for p in pros:
            st.markdown(f" {p}")
    else:
        st.caption("No pros on record for this company yet.")
with pcol2:
    st.markdown("**Cons**")
    cons = pc["cons"].dropna().tolist() if not pc.empty else []
    if cons:
        for c in cons:
            st.markdown(f" {c}")
    else:
        st.caption("No cons on record for this company yet.")