import os
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "nifty100.db")


def _connect() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. Place nifty100.db in the data/ folder."
        )
    return sqlite3.connect(DB_PATH)


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    conn = _connect()
    try:
        companies = pd.read_sql("SELECT * FROM companies", conn)
        sectors = pd.read_sql("SELECT company_id, broad_sector, sub_sector, index_weight_pct, market_cap_category FROM sectors", conn)
        latest_year = pd.read_sql("SELECT MAX(year) AS y FROM financial_ratios", conn)["y"].iloc[0]
        ratios = pd.read_sql(
            "SELECT * FROM financial_ratios WHERE year = ?", conn, params=(latest_year,)
        )
        df = companies.merge(sectors, left_on="id", right_on="company_id", how="left")
        df = df.merge(ratios, on="company_id", how="left", suffixes=("", "_ratio"))
        df["company_name"] = (
            df["company_name"].astype(str).str.split("\n").str[0].str.strip()
        )
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_ratios(ticker: str, year: str | None = None) -> pd.DataFrame:
    conn = _connect()
    try:
        if year:
            df = pd.read_sql(
                "SELECT * FROM financial_ratios WHERE company_id = ? AND year = ? ORDER BY year",
                conn, params=(ticker, year),
            )
        else:
            df = pd.read_sql(
                "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year",
                conn, params=(ticker,),
            )
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_pl(ticker: str) -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql(
            "SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year", conn, params=(ticker,)
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_bs(ticker: str) -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql(
            "SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year", conn, params=(ticker,)
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_cf(ticker: str) -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql(
            "SELECT * FROM cashflow WHERE company_id = ? ORDER BY year", conn, params=(ticker,)
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql("SELECT * FROM sectors", conn)
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_peers(group_name: str) -> pd.DataFrame:
    conn = _connect()
    try:
        members = pd.read_sql(
            "SELECT * FROM peer_groups WHERE peer_group_name = ?", conn, params=(group_name,)
        )
        latest_year = pd.read_sql("SELECT MAX(year) AS y FROM financial_ratios", conn)["y"].iloc[0]
        ratios = pd.read_sql(
            "SELECT * FROM financial_ratios WHERE year = ?", conn, params=(latest_year,)
        )
        companies = pd.read_sql("SELECT id, company_name FROM companies", conn)
        companies["company_name"] = (
            companies["company_name"].astype(str).str.split("\n").str[0].str.strip()
        )
        df = members.merge(ratios, on="company_id", how="left")
        df = df.merge(companies, left_on="company_id", right_on="id", how="left")
        return df
    finally:
        conn.close()
@st.cache_data(ttl=600)
def get_peer_percentiles(group_name: str, ticker: str | None = None) -> pd.DataFrame:
    conn = _connect()
    try:
        if ticker:
            return pd.read_sql(
                "SELECT * FROM peer_percentiles WHERE peer_group_name = ? AND company_id = ?",
                conn, params=(group_name, ticker),
            )
        return pd.read_sql(
            "SELECT * FROM peer_percentiles WHERE peer_group_name = ?", conn, params=(group_name,)
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_peer_groups_list() -> list[str]:
    conn = _connect()
    try:
        df = pd.read_sql("SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY peer_group_name", conn)
        return df["peer_group_name"].tolist()
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_company_peer_group(ticker: str) -> str | None:
    conn = _connect()
    try:
        df = pd.read_sql(
            "SELECT peer_group_name FROM peer_groups WHERE company_id = ? LIMIT 1", conn, params=(ticker,)
        )
        if df.empty:
            return None
        return df["peer_group_name"].iloc[0]
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_valuation(ticker: str) -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql(
            """SELECT year, market_cap_crore, enterprise_value_crore, pe_ratio,
                      pb_ratio, ev_ebitda, dividend_yield_pct, free_cash_flow_cr
               FROM financial_ratios WHERE company_id = ? ORDER BY year""",
            conn, params=(ticker,),
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_documents(ticker: str) -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql(
            "SELECT * FROM documents WHERE company_id = ? ORDER BY year DESC", conn, params=(ticker,)
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_pros_cons(ticker: str) -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql(
            "SELECT * FROM prosandcons WHERE company_id = ?", conn, params=(ticker,)
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_all_financial_ratios() -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql("SELECT * FROM financial_ratios", conn)
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_capital_allocation() -> pd.DataFrame:
    conn = _connect()
    try:
        cf = pd.read_sql("SELECT * FROM cashflow", conn)
    finally:
        conn.close()

    if cf.empty:
        return pd.DataFrame(columns=["company_id", "year", "pattern_label"])

    cf = cf.sort_values("year")
    latest = cf.groupby("company_id").tail(1).copy()

    def sign(x):
        if pd.isna(x):
            return None
        return "+" if x >= 0 else "-"

    latest["cfo_sign"] = latest["operating_activity"].apply(sign)
    latest["cfi_sign"] = latest["investing_activity"].apply(sign)
    latest["cff_sign"] = latest["financing_activity"].apply(sign)

    pattern_labels = {
        ("+", "-", "-"): "Mature Compounder",
        ("+", "-", "+"): "Growth Funded by Capital Raise",
        ("+", "+", "-"): "Harvesting / Returning Capital",
        ("+", "+", "+"): "Building Cash Reserve",
        ("-", "-", "-"): "Aggressive Cash Burn",
        ("-", "-", "+"): "Distress: Growth Funded by Debt/Equity",
        ("-", "+", "-"): "Divesting to Repay Debt",
        ("-", "+", "+"): "Severe Distress",
    }

    def label_row(r):
        key = (r["cfo_sign"], r["cfi_sign"], r["cff_sign"])
        if None in key:
            return "Insufficient Data"
        return pattern_labels.get(key, "Unclassified")

    latest["pattern_label"] = latest.apply(label_row, axis=1)
    return latest[["company_id", "year", "operating_activity", "investing_activity",
                    "financing_activity", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"]]