"""
src/etl/validator.py

Implements DQ-01 through DQ-16 for Sprint 1 / Day 03.

Each rule function takes the relevant DataFrame(s) and returns a list
of failure dicts:
    {"rule": "DQ-01", "severity": "CRITICAL"/"WARNING", "table": ...,
     "row_id": ..., "detail": ...}

run_all_rules() runs every rule against a dict of DataFrames (as
produced by loader.load_all_raw()) and returns one combined list,
which the caller writes to output/validation_failures.csv.

CRITICAL rules (must be zero before Day 05 load proceeds):
    DQ-01  PK uniqueness (per-table `id` column)
    DQ-02  (company_id, year) composite key uniqueness
    DQ-03  FK integrity — company_id must exist in companies.id

WARNING rules (logged, do not block the load):
    DQ-04  Balance sheet balances: total_assets ~= total_liabilities (<1%)
    DQ-05  OPM cross-check: operating_profit/sales ~= opm_percentage
    DQ-06  Positive sales
    DQ-07  Net cash flow consistency: operating+investing+financing ~= net_cash_flow
    DQ-08  Tax rate sanity range (0-60%)
    DQ-09  Dividend payout ratio cap (<=100%)
    DQ-10  Annual report URL format validity
    DQ-11  EPS sign consistency with net_profit sign
    DQ-12  BSE profile URL presence (companies)
    DQ-13  NSE profile URL presence (companies)
    DQ-14  Website URL format validity (companies)
    DQ-15  Year coverage: flag companies with <5 distinct years of P&L data
    DQ-16  Stock price positivity (open/high/low/close > 0)
"""

import re
from typing import Dict, List

import pandas as pd


URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _fail(rule: str, severity: str, table: str, row_id, detail: str) -> dict:
    return {"rule": rule, "severity": severity, "table": table, "row_id": row_id, "detail": detail}


# ---------------------------------------------------------------------
# CRITICAL rules
# ---------------------------------------------------------------------

def dq01_pk_uniqueness(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-01: `id` column must be unique within each table (companies uses `id`=ticker)."""
    failures = []
    for name, df in tables.items():
        pk_col = "id" if "id" in df.columns else None
        if pk_col is None:
            continue
        dupes = df[df.duplicated(subset=[pk_col], keep=False)]
        for _, row in dupes.iterrows():
            failures.append(_fail("DQ-01", "CRITICAL", name, row[pk_col],
                                   f"duplicate primary key value: {row[pk_col]}"))
    return failures


def dq02_composite_key_uniqueness(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-02: (company_id, year) must be unique in each year-keyed table."""
    failures = []
    year_tables = ["profitandloss", "balancesheet", "cashflow", "financial_ratios"]
    for name in year_tables:
        df = tables.get(name)
        if df is None or "company_id" not in df.columns or "year" not in df.columns:
            continue
        dupes = df[df.duplicated(subset=["company_id", "year"], keep=False)]
        for _, row in dupes.iterrows():
            failures.append(_fail("DQ-02", "CRITICAL", name, row.get("id"),
                                   f"duplicate (company_id, year): ({row['company_id']}, {row['year']})"))
    return failures


def dq03_fk_integrity(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-03: every company_id must exist in companies.id."""
    failures = []
    companies_df = tables.get("companies")
    if companies_df is None:
        return failures
    valid_ids = set(companies_df["id"].dropna())

    for name, df in tables.items():
        if name == "companies" or "company_id" not in df.columns:
            continue
        bad = df[~df["company_id"].isin(valid_ids)]
        for _, row in bad.iterrows():
            failures.append(_fail("DQ-03", "CRITICAL", name, row.get("id"),
                                   f"company_id {row['company_id']!r} not found in companies.id"))
    return failures


# ---------------------------------------------------------------------
# WARNING rules
# ---------------------------------------------------------------------

def dq04_balance_sheet_balances(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-04: total_assets should equal total_liabilities within 1%."""
    failures = []
    df = tables.get("balancesheet")
    if df is None:
        return failures
    for _, row in df.iterrows():
        ta, tl = row.get("total_assets"), row.get("total_liabilities")
        if pd.isna(ta) or pd.isna(tl) or tl == 0:
            continue
        pct_diff = abs(ta - tl) / abs(tl)
        if pct_diff > 0.01:
            failures.append(_fail("DQ-04", "WARNING", "balancesheet", row.get("id"),
                                   f"total_assets ({ta}) vs total_liabilities ({tl}) differ by {pct_diff:.2%}"))
    return failures


def dq05_opm_cross_check(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-05: operating_profit/sales should roughly match opm_percentage."""
    failures = []
    df = tables.get("profitandloss")
    if df is None:
        return failures
    for _, row in df.iterrows():
        sales, op, opm = row.get("sales"), row.get("operating_profit"), row.get("opm_percentage")
        if pd.isna(sales) or pd.isna(op) or pd.isna(opm) or sales == 0:
            continue
        computed_opm = (op / sales) * 100
        if abs(computed_opm - opm) > 2:  # 2 percentage-point tolerance
            failures.append(_fail("DQ-05", "WARNING", "profitandloss", row.get("id"),
                                   f"computed OPM {computed_opm:.1f}% vs reported {opm}%"))
    return failures


def dq06_positive_sales(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-06: sales should be positive."""
    failures = []
    df = tables.get("profitandloss")
    if df is None:
        return failures
    bad = df[df["sales"] <= 0]
    for _, row in bad.iterrows():
        failures.append(_fail("DQ-06", "WARNING", "profitandloss", row.get("id"),
                               f"non-positive sales: {row['sales']}"))
    return failures


def dq07_net_cash_flow_consistency(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-07: operating + investing + financing should equal net_cash_flow."""
    failures = []
    df = tables.get("cashflow")
    if df is None:
        return failures
    for _, row in df.iterrows():
        op, inv, fin, net = (row.get("operating_activity"), row.get("investing_activity"),
                              row.get("financing_activity"), row.get("net_cash_flow"))
        if any(pd.isna(v) for v in (op, inv, fin, net)):
            continue
        computed = op + inv + fin
        if abs(computed - net) > 1:  # tolerance of 1 crore for rounding
            failures.append(_fail("DQ-07", "WARNING", "cashflow", row.get("id"),
                                   f"computed net cash {computed} vs reported {net}"))
    return failures


def dq08_tax_rate_sanity(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-08: tax_percentage should fall within a sane 0-60% range."""
    failures = []
    df = tables.get("profitandloss")
    if df is None:
        return failures
    bad = df[(df["tax_percentage"] < 0) | (df["tax_percentage"] > 60)]
    for _, row in bad.iterrows():
        failures.append(_fail("DQ-08", "WARNING", "profitandloss", row.get("id"),
                               f"tax_percentage out of sane range: {row['tax_percentage']}"))
    return failures


def dq09_dividend_payout_cap(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-09: dividend_payout should not exceed 100%."""
    failures = []
    df = tables.get("profitandloss")
    if df is None:
        return failures
    bad = df[df["dividend_payout"] > 100]
    for _, row in bad.iterrows():
        failures.append(_fail("DQ-09", "WARNING", "profitandloss", row.get("id"),
                               f"dividend_payout exceeds 100%: {row['dividend_payout']}"))
    return failures


def dq10_annual_report_url_format(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-10: annual_report_url should look like a valid http(s) URL."""
    failures = []
    df = tables.get("documents")
    if df is None:
        return failures
    for _, row in df.iterrows():
        url = row.get("annual_report_url")
        if pd.isna(url) or not URL_RE.match(str(url)):
            failures.append(_fail("DQ-10", "WARNING", "documents", row.get("id"),
                                   f"invalid or missing URL: {url!r}"))
    return failures


def dq11_eps_sign_consistency(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-11: eps sign should match net_profit sign."""
    failures = []
    df = tables.get("profitandloss")
    if df is None:
        return failures
    for _, row in df.iterrows():
        eps, net_profit = row.get("eps"), row.get("net_profit")
        if pd.isna(eps) or pd.isna(net_profit):
            continue
        if (eps > 0 and net_profit < 0) or (eps < 0 and net_profit > 0):
            failures.append(_fail("DQ-11", "WARNING", "profitandloss", row.get("id"),
                                   f"eps ({eps}) sign inconsistent with net_profit ({net_profit})"))
    return failures


def dq12_bse_profile_presence(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-12: companies should have a non-empty bse_profile URL."""
    failures = []
    df = tables.get("companies")
    if df is None:
        return failures
    bad = df[df["bse_profile"].isna() | (df["bse_profile"] == "")]
    for _, row in bad.iterrows():
        failures.append(_fail("DQ-12", "WARNING", "companies", row.get("id"),
                               "missing bse_profile URL"))
    return failures


def dq13_nse_profile_presence(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-13: companies should have a non-empty nse_profile URL."""
    failures = []
    df = tables.get("companies")
    if df is None:
        return failures
    bad = df[df["nse_profile"].isna() | (df["nse_profile"] == "")]
    for _, row in bad.iterrows():
        failures.append(_fail("DQ-13", "WARNING", "companies", row.get("id"),
                               "missing nse_profile URL"))
    return failures


def dq14_website_url_format(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-14: companies.website should look like a valid http(s) URL."""
    failures = []
    df = tables.get("companies")
    if df is None:
        return failures
    for _, row in df.iterrows():
        url = row.get("website")
        if pd.isna(url) or not URL_RE.match(str(url)):
            failures.append(_fail("DQ-14", "WARNING", "companies", row.get("id"),
                                   f"invalid or missing website URL: {url!r}"))
    return failures


def dq15_year_coverage(tables: Dict[str, pd.DataFrame], min_years: int = 5) -> List[dict]:
    """DQ-15: flag companies with fewer than min_years of profitandloss coverage."""
    failures = []
    df = tables.get("profitandloss")
    if df is None:
        return failures
    coverage = df.groupby("company_id")["year"].nunique()
    thin = coverage[coverage < min_years]
    for company_id, n_years in thin.items():
        failures.append(_fail("DQ-15", "WARNING", "profitandloss", company_id,
                               f"only {n_years} distinct year(s) of data (< {min_years})"))
    return failures


def dq16_stock_price_positivity(tables: Dict[str, pd.DataFrame]) -> List[dict]:
    """DQ-16: open/high/low/close prices should all be positive."""
    failures = []
    df = tables.get("stock_prices")
    if df is None:
        return failures
    price_cols = ["open_price", "high_price", "low_price", "close_price"]
    for _, row in df.iterrows():
        for col in price_cols:
            val = row.get(col)
            if pd.notna(val) and val <= 0:
                failures.append(_fail("DQ-16", "WARNING", "stock_prices", row.get("id"),
                                       f"non-positive {col}: {val}"))
    return failures


# ---------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------

ALL_RULES = [
    dq01_pk_uniqueness,
    dq02_composite_key_uniqueness,
    dq03_fk_integrity,
    dq04_balance_sheet_balances,
    dq05_opm_cross_check,
    dq06_positive_sales,
    dq07_net_cash_flow_consistency,
    dq08_tax_rate_sanity,
    dq09_dividend_payout_cap,
    dq10_annual_report_url_format,
    dq11_eps_sign_consistency,
    dq12_bse_profile_presence,
    dq13_nse_profile_presence,
    dq14_website_url_format,
    dq15_year_coverage,
    dq16_stock_price_positivity,
]


def run_all_rules(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Run all 16 DQ rules and return a combined DataFrame of failures."""
    all_failures: List[dict] = []
    for rule_fn in ALL_RULES:
        all_failures.extend(rule_fn(tables))
    return pd.DataFrame(all_failures, columns=["rule", "severity", "table", "row_id", "detail"])


def has_critical_failures(failures_df: pd.DataFrame) -> bool:
    """Return True if any CRITICAL-severity failures exist (blocks Day 05 load)."""
    if failures_df.empty:
        return False
    return (failures_df["severity"] == "CRITICAL").any()


if __name__ == "__main__":
    from src.etl.loader import load_all_raw

    tables = load_all_raw()
    failures_df = run_all_rules(tables)

    print(f"Total DQ failures: {len(failures_df)}")
    if not failures_df.empty:
        print(failures_df["severity"].value_counts())

    failures_df.to_csv("output/validation_failures.csv", index=False)
    print("Written to output/validation_failures.csv")

    if has_critical_failures(failures_df):
        print("\n*** CRITICAL failures found — resolve before Day 05 load. ***")
    else:
        print("\nNo CRITICAL failures. Safe to proceed to Day 05 load.")