import streamlit as st
import pandas as pd
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_all_financial_ratios, get_companies

st.set_page_config(page_title="Screener | Nifty 100 Analytics", layout="wide")
st.title(" Financial Screener")

ratios = get_all_financial_ratios()
companies = get_companies()[["id", "company_name", "broad_sector"]].rename(columns={"id": "company_id"})

latest_year = ratios["year"].max()
data = ratios[ratios["year"] == latest_year].merge(companies, on="company_id", how="left")

PRESETS = {
    "None (custom)": None,
    "Quality": dict(roe_min=15, de_max=1.0, fcf_min=0, rev_cagr_min=10, pat_cagr_min=0, opm_min=0, pe_max=100, pb_max=100, div_yield_min=0, icr_min=0),
    "Value": dict(roe_min=0, de_max=2.0, fcf_min=-1e9, rev_cagr_min=-100, pat_cagr_min=-100, opm_min=0, pe_max=20, pb_max=3, div_yield_min=1, icr_min=0),
    "Growth": dict(roe_min=0, de_max=2.0, fcf_min=-1e9, rev_cagr_min=15, pat_cagr_min=20, opm_min=0, pe_max=100, pb_max=100, div_yield_min=0, icr_min=0),
    "Dividend": dict(roe_min=0, de_max=100, fcf_min=0, rev_cagr_min=-100, pat_cagr_min=-100, opm_min=0, pe_max=100, pb_max=100, div_yield_min=2, icr_min=0),
    "Debt-Free": dict(roe_min=12, de_max=0.0, fcf_min=-1e9, rev_cagr_min=-100, pat_cagr_min=-100, opm_min=0, pe_max=100, pb_max=100, div_yield_min=0, icr_min=0),
    "Turnaround": dict(roe_min=-100, de_max=100, fcf_min=-1e9, rev_cagr_min=10, pat_cagr_min=-100, opm_min=0, pe_max=100, pb_max=100, div_yield_min=0, icr_min=0),
}

st.sidebar.subheader("Preset Screeners")
preset_choice = st.sidebar.selectbox("Choose a preset", list(PRESETS.keys()))
p = PRESETS[preset_choice] or {}

st.sidebar.subheader("Custom Filters")
roe_min = st.sidebar.slider("ROE min (%)", -50, 100, int(p.get("roe_min", 0)))
de_max = st.sidebar.slider("D/E max", 0.0, 10.0, float(p.get("de_max", 5.0)), step=0.1)
fcf_min = st.sidebar.number_input("FCF min (₹Cr)", value=float(p.get("fcf_min", -1e9)), step=100.0)
rev_cagr_min = st.sidebar.slider("Revenue CAGR min (%, 5yr)", -50, 100, int(p.get("rev_cagr_min", -100)))
pat_cagr_min = st.sidebar.slider("PAT CAGR min (%, 5yr)", -50, 100, int(p.get("pat_cagr_min", -100)))
opm_min = st.sidebar.slider("OPM min (%)", 0, 60, int(p.get("opm_min", 0)))
pe_max = st.sidebar.slider("P/E max", 0, 150, int(p.get("pe_max", 100)))
pb_max = st.sidebar.slider("P/B max", 0.0, 30.0, float(p.get("pb_max", 100.0)))
div_yield_min = st.sidebar.slider("Dividend Yield min (%)", 0.0, 10.0, float(p.get("div_yield_min", 0.0)), step=0.1)
icr_min = st.sidebar.slider("Interest Coverage min", 0, 50, int(p.get("icr_min", 0)))

def col_or_nan(df, col):
    return df[col] if col in df.columns else pd.Series([float("nan")] * len(df), index=df.index)

mask = pd.Series(True, index=data.index)
mask &= col_or_nan(data, "return_on_equity_pct").fillna(-9999) >= roe_min
mask &= col_or_nan(data, "debt_to_equity").fillna(9999) <= de_max
mask &= col_or_nan(data, "free_cash_flow_cr").fillna(-1e12) >= fcf_min
mask &= col_or_nan(data, "revenue_cagr_5yr").fillna(-9999) >= rev_cagr_min
mask &= col_or_nan(data, "pat_cagr_5yr").fillna(-9999) >= pat_cagr_min
mask &= col_or_nan(data, "operating_profit_margin_pct").fillna(-9999) >= opm_min
mask &= col_or_nan(data, "pe_ratio").fillna(0) <= pe_max
mask &= col_or_nan(data, "pb_ratio").fillna(0) <= pb_max
mask &= col_or_nan(data, "dividend_yield_pct").fillna(-1) >= div_yield_min
mask &= col_or_nan(data, "interest_coverage").fillna(9999) >= icr_min

results = data[mask].copy()

display_cols = [
    "company_id", "company_name", "broad_sector", "composite_quality_score",
    "return_on_equity_pct", "debt_to_equity", "free_cash_flow_cr",
    "revenue_cagr_5yr", "pat_cagr_5yr", "operating_profit_margin_pct",
    "pe_ratio", "pb_ratio", "dividend_yield_pct", "interest_coverage",
]
display_cols = [c for c in display_cols if c in results.columns]
results_sorted = results.sort_values("composite_quality_score", ascending=False, na_position="last") if "composite_quality_score" in results.columns else results

st.markdown(f"**{len(results_sorted)} companies match your filters**")

st.dataframe(
    results_sorted[display_cols].rename(columns={
        "company_id": "Ticker", "company_name": "Company", "broad_sector": "Sector",
        "composite_quality_score": "Quality Score", "return_on_equity_pct": "ROE %",
        "debt_to_equity": "D/E", "free_cash_flow_cr": "FCF (₹Cr)",
        "revenue_cagr_5yr": "Rev CAGR 5yr %", "pat_cagr_5yr": "PAT CAGR 5yr %",
        "operating_profit_margin_pct": "OPM %", "pe_ratio": "P/E", "pb_ratio": "P/B",
        "dividend_yield_pct": "Div Yield %", "interest_coverage": "ICR",
    }),
    hide_index=True, use_container_width=True, height=480,
)

csv = results_sorted[display_cols].to_csv(index=False).encode("utf-8")
st.download_button("⬇ Download results as CSV", data=csv, file_name="screener_results.csv", mime="text/csv")