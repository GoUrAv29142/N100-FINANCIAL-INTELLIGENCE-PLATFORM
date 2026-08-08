import streamlit as st
import pandas as pd
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_companies, get_documents

st.set_page_config(page_title="Annual Reports | Nifty 100 Analytics", layout="wide")
st.title(" Annual Reports")

companies = get_companies()
search_options = (companies["id"] + " — " + companies["company_name"].astype(str).str.strip()).sort_values().tolist()

query = st.text_input("Search company", "")
filtered = [o for o in search_options if query.lower() in o.lower()] if query else search_options
if not filtered:
    st.warning("Ticker not found — please try another")
    st.stop()
selection = st.selectbox("Company", options=filtered)
ticker = selection.split(" — ")[0]

docs = get_documents(ticker)
if docs.empty:
    st.info("No annual report records found for this company.")
    st.stop()

years = sorted(docs["year"].dropna().unique().tolist(), reverse=True)
year_filter = st.multiselect("Filter by year", options=years, default=years)

docs_filtered = docs[docs["year"].isin(year_filter)]

st.subheader(f"Available Reports — {ticker}")
for _, r in docs_filtered.iterrows():
    url = r.get("annual_report_url")
    col1, col2 = st.columns([1, 4])
    with col1:
        st.write(f"**{r['year']}**")
    with col2:
        if pd.notna(url) and str(url).strip():
            st.markdown(f"[ Open Annual Report]({url})")
        else:
            st.markdown(":red[Report unavailable]")

st.caption(
    "Note: links are validated with an HTTP check during ETL (DQ-13). "
    "A 404 or missing URL shows as **Report unavailable** above rather than a broken link."
)