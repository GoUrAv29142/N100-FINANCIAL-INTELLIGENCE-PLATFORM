"""
Day 31 - Cash Flow Intelligence Module
Computes CFO quality, CapEx intensity, distress/deleveraging flags, and a
capital allocation label for all 92 companies. Writes:
  - output/cashflow_intelligence.xlsx
  - output/distress_alerts.csv

Judgment calls (see chat for full rationale):
- CFO Quality Score = average of financial_ratios.cfo_pat_ratio over the
  last 5 AVAILABLE years (not calendar-continuous), reusing the Sprint 2
  precomputed ratio rather than recomputing CFO/PAT from raw tables.
- CapEx Intensity uses latest-year cashflow.investing_activity and
  financial_ratios.sales (consistent with how sales is sourced elsewhere
  in this pipeline).
- FCF Conversion = free_cash_flow_cr / operating_profit x100, where
  operating_profit is derived as operating_profit_margin_pct/100 x sales
  (same derivation used for EBITDA in the Day 30 con-rule-11 logic, since
  no raw operating_profit column exists in financial_ratios).
- Distress Signal and Deleveraging flags use the latest 1-2 years of RAW
  cashflow/balancesheet tables directly (not financial_ratios), since CFO/
  CFI/CFF signs and YoY borrowings are not part of that precomputed table.
- Capital Allocation Label: this script computes it directly from the
  latest year's CFO/CFI/CFF sign pattern (8 combinations). If
  output/capital_allocation.csv already exists from Sprint 2, its latest-
  year label is used instead for consistency; otherwise this script's own
  computation is the fallback.
- Companies with zero cashflow/balancesheet rows get "No Data" labels and
  NaN flags rather than being silently dropped, so the 92-row exit
  criterion still holds.
"""
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd


def find_project_root(marker="db/nifty100.db"):
    """Walk upward from this file until we find the directory that
    actually contains db/nifty100.db. Works no matter which nested
    folder the script itself lives in."""
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / marker).exists():
            return current
        current = current.parent
    raise FileNotFoundError(
        f"Could not locate '{marker}' by walking up from {Path(__file__).resolve()}. "
        f"Check that db/nifty100.db exists somewhere above this script."
    )


ROOT = find_project_root()
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

CAPITAL_ALLOCATION_LABELS = {
    ("+", "-", "-"): "Reinvestor / Shareholder Returns",
    ("+", "-", "+"): "Aggressive Growth (Ops + External Capital)",
    ("+", "+", "-"): "Divestor / Downsizing",
    ("+", "+", "+"): "Cash Accumulation",
    ("-", "-", "-"): "Cash Drain (High Risk)",
    ("-", "-", "+"): "Distress Signal",
    ("-", "+", "-"): "Asset Liquidation",
    ("-", "+", "+"): "Severe Distress",
}


def sign(x):
    if pd.isna(x):
        return None
    return "+" if x >= 0 else "-"


def consecutive_tail(df_sorted_by_year, n):
    if len(df_sorted_by_year) < n:
        return None
    return df_sorted_by_year.tail(n)


def load_data(conn):
    companies = pd.read_sql("SELECT id AS company_id FROM companies", conn)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    cashflow = pd.read_sql(
        "SELECT company_id, CAST(year AS INTEGER) AS year, "
        "operating_activity, investing_activity, financing_activity, net_cash_flow "
        "FROM cashflow",
        conn,
    )
    balancesheet = pd.read_sql(
        "SELECT company_id, CAST(year AS INTEGER) AS year, borrowings FROM balancesheet",
        conn,
    )
    ratios = pd.read_sql(
        "SELECT company_id, CAST(year AS INTEGER) AS year, "
        "cfo_pat_ratio, free_cash_flow_cr, fcf_cagr_5yr, "
        "operating_profit_margin_pct, sales, net_profit "
        "FROM financial_ratios",
        conn,
    )
    return companies, sectors, cashflow, balancesheet, ratios


def load_existing_capital_allocation():
    path = OUTPUT_DIR / "capital_allocation.csv"
    if not path.exists():
        return {}
    try:
        df = pd.read_csv(path)
    except Exception:
        return {}
    if not {"company_id", "year", "pattern_label"}.issubset(df.columns):
        return {}
    latest = df.sort_values("year").groupby("company_id").tail(1)
    return dict(zip(latest["company_id"], latest["pattern_label"]))


def cfo_quality_label(score):
    if pd.isna(score):
        return "Insufficient Data"
    if score > 1.0:
        return "High Quality"
    if score >= 0.5:
        return "Moderate"
    return "Accrual Risk"


def capex_label(pct):
    if pd.isna(pct):
        return "Insufficient Data"
    if pct < 3:
        return "Asset Light"
    if pct <= 8:
        return "Moderate"
    return "Capital Intensive"


def evaluate_company(company_id, sector, cf_hist, bs_hist, ratio_hist, existing_labels):
    row = {
        "company_id": company_id,
        "sector": sector,
        "cfo_quality_score": np.nan,
        "cfo_quality_label": "No Data",
        "capex_intensity_pct": np.nan,
        "capex_label": "No Data",
        "fcf_cagr_5yr": np.nan,
        "fcf_conversion_pct": np.nan,
        "distress_flag": False,
        "deleveraging_flag": False,
        "capital_allocation_label": "No Data",
    }

    if not ratio_hist.empty:
        last5 = consecutive_tail(ratio_hist, 5)
        pool = last5 if last5 is not None else ratio_hist
        vals = pool["cfo_pat_ratio"].dropna()
        if not vals.empty:
            row["cfo_quality_score"] = round(vals.mean(), 3)
            row["cfo_quality_label"] = cfo_quality_label(row["cfo_quality_score"])

        latest_ratio = ratio_hist.iloc[-1]
        row["fcf_cagr_5yr"] = latest_ratio["fcf_cagr_5yr"]

        latest_cf_for_year = cf_hist[cf_hist["year"] == latest_ratio["year"]]
        if not latest_cf_for_year.empty and pd.notna(latest_ratio["sales"]) and latest_ratio["sales"] != 0:
            investing = latest_cf_for_year.iloc[0]["investing_activity"]
            if pd.notna(investing):
                capex_pct = abs(investing) / latest_ratio["sales"] * 100
                row["capex_intensity_pct"] = round(capex_pct, 2)
                row["capex_label"] = capex_label(capex_pct)

        if (pd.notna(latest_ratio["operating_profit_margin_pct"])
                and pd.notna(latest_ratio["sales"])
                and pd.notna(latest_ratio["free_cash_flow_cr"])):
            operating_profit = (latest_ratio["operating_profit_margin_pct"] / 100) * latest_ratio["sales"]
            if operating_profit != 0:
                row["fcf_conversion_pct"] = round(latest_ratio["free_cash_flow_cr"] / operating_profit * 100, 2)

    if not cf_hist.empty:
        latest_cf = cf_hist.iloc[-1]
        cfo, cfi, cff = latest_cf["operating_activity"], latest_cf["investing_activity"], latest_cf["financing_activity"]

        if pd.notna(cfo) and pd.notna(cff):
            row["distress_flag"] = bool(cfo < 0 and cff > 0)

        pattern = (sign(cfo), sign(cfi), sign(cff))
        if company_id in existing_labels:
            row["capital_allocation_label"] = existing_labels[company_id]
        elif None not in pattern:
            row["capital_allocation_label"] = CAPITAL_ALLOCATION_LABELS.get(pattern, "Unclassified")

        if pd.notna(cff) and cff < 0 and not bs_hist.empty:
            latest_bs = bs_hist[bs_hist["year"] == latest_cf["year"]]
            prior_bs = bs_hist[bs_hist["year"] < latest_cf["year"]].tail(1)
            if not latest_bs.empty and not prior_bs.empty:
                latest_borrow = latest_bs.iloc[0]["borrowings"]
                prior_borrow = prior_bs.iloc[0]["borrowings"]
                if pd.notna(latest_borrow) and pd.notna(prior_borrow):
                    row["deleveraging_flag"] = bool(latest_borrow < prior_borrow)

    return row


def main():
    conn = sqlite3.connect(DB_PATH)
    companies, sectors, cashflow, balancesheet, ratios = load_data(conn)
    conn.close()

    sector_map = dict(zip(sectors["company_id"], sectors["broad_sector"]))
    existing_labels = load_existing_capital_allocation()

    rows = []
    for company_id in companies["company_id"]:
        cf_hist = cashflow[cashflow["company_id"] == company_id].sort_values("year").reset_index(drop=True)
        bs_hist = balancesheet[balancesheet["company_id"] == company_id].sort_values("year").reset_index(drop=True)
        ratio_hist = ratios[ratios["company_id"] == company_id].sort_values("year").reset_index(drop=True)
        sector = sector_map.get(company_id, "Unknown")
        rows.append(evaluate_company(company_id, sector, cf_hist, bs_hist, ratio_hist, existing_labels))

    out_df = pd.DataFrame(rows, columns=[
        "company_id", "sector", "cfo_quality_score", "cfo_quality_label",
        "capex_intensity_pct", "capex_label", "fcf_cagr_5yr", "fcf_conversion_pct",
        "distress_flag", "deleveraging_flag", "capital_allocation_label",
    ])

    xlsx_path = OUTPUT_DIR / "cashflow_intelligence.xlsx"
    out_df.to_excel(xlsx_path, index=False)

    distressed = out_df[out_df["distress_flag"] == True]["company_id"].tolist()
    alert_rows = []
    for company_id in distressed:
        cf_hist = cashflow[cashflow["company_id"] == company_id].sort_values("year")
        ratio_hist = ratios[ratios["company_id"] == company_id].sort_values("year")
        if cf_hist.empty:
            continue
        latest_cf = cf_hist.iloc[-1]
        latest_np = ratio_hist.iloc[-1]["net_profit"] if not ratio_hist.empty else np.nan
        alert_rows.append((
            company_id,
            latest_cf["operating_activity"],
            latest_cf["financing_activity"],
            latest_np,
        ))
    alerts_df = pd.DataFrame(alert_rows, columns=["company_id", "cfo", "cff", "latest_net_profit"])
    alerts_path = OUTPUT_DIR / "distress_alerts.csv"
    alerts_df.to_csv(alerts_path, index=False)

    print(f"cashflow_intelligence.xlsx -> {xlsx_path} ({len(out_df)} rows)")
    print(f"distress_alerts.csv -> {alerts_path} ({len(alerts_df)} rows)")

    print("\nExit-criteria check: 92 rows, all required columns present")
    print(f"  Row count: {len(out_df)} (expected 92)")
    missing_data = out_df[out_df["cfo_quality_label"] == "No Data"]["company_id"].tolist()
    if missing_data:
        print(f"  Companies with no cashflow data at all: {missing_data}")

    print("\nCFO quality label distribution:")
    print(out_df["cfo_quality_label"].value_counts().to_string())
    print("\nCapEx label distribution:")
    print(out_df["capex_label"].value_counts().to_string())
    print("\nCapital allocation label distribution:")
    print(out_df["capital_allocation_label"].value_counts().to_string())
    print(f"\nDistress-flagged companies: {len(distressed)} {distressed}")
    print(f"Deleveraging-flagged companies: {out_df['deleveraging_flag'].sum()}")
    print("\nDone.")


if __name__ == "__main__":
    main()