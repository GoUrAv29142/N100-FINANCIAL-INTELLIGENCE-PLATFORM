import sqlite3
import pandas as pd

conn = sqlite3.connect(r"db\nifty100.db")

# 1. Sector classification - which label means "financial company"?
sectors = pd.read_sql(
    "SELECT broad_sector, COUNT(*) as n FROM sectors GROUP BY broad_sector ORDER BY n DESC",
    conn,
)
print("=== broad_sector distinct values ===")
print(sectors.to_string(index=False))

# 2. Does every company have financial_ratios data at all?
all_companies = set(pd.read_sql("SELECT id FROM companies", conn)["id"])
ratios = pd.read_sql("SELECT company_id, CAST(year AS INTEGER) as year FROM financial_ratios", conn)
covered = set(ratios["company_id"].unique())
missing = all_companies - covered
print(f"\n=== Company coverage in financial_ratios ===")
print(f"Total companies: {len(all_companies)}, with at least 1 row: {len(covered)}")
if missing:
    print(f"Companies with ZERO financial_ratios rows: {sorted(missing)}")

# 3. Year coverage / gaps per company
year_stats = ratios.groupby("company_id")["year"].agg(["min", "max", "count"]).reset_index()
year_stats["expected_if_no_gaps"] = year_stats["max"] - year_stats["min"] + 1
year_stats["has_gaps"] = year_stats["count"] < year_stats["expected_if_no_gaps"]
print(f"\n=== Year coverage per company ===")
print(f"Companies with calendar-year gaps: {year_stats['has_gaps'].sum()} / {len(year_stats)}")
print(f"Years available per company - min: {year_stats['count'].min()}, "
      f"max: {year_stats['count'].max()}, median: {year_stats['count'].median()}")
under_3 = year_stats[year_stats["count"] < 3]
print(f"\nCompanies with fewer than 3 years of data (blocks any 3yr-consecutive rule): {len(under_3)}")
if not under_3.empty:
    print(under_3.to_string(index=False))

# 4. Null coverage on latest-year snapshot for rule-relevant columns
cols = sorted(set([
    "return_on_equity_pct", "free_cash_flow_cr", "debt_to_equity",
    "revenue_cagr_5yr", "revenue_cagr_3yr", "operating_profit_margin_pct",
    "pat_cagr_5yr", "interest_coverage", "icr_label", "dividend_yield_pct",
    "eps_cagr_5yr", "earnings_per_share", "net_profit", "sales",
    "dividend_payout_ratio_pct", "return_on_capital_employed_pct",
    "total_debt_cr", "asset_turnover",
]))
col_list = ", ".join(cols)
full = pd.read_sql(
    f"SELECT company_id, CAST(year AS INTEGER) as year, {col_list} FROM financial_ratios",
    conn,
)
latest = full.sort_values("year").groupby("company_id").tail(1)
print(f"\n=== Non-null coverage on latest-year snapshot (n={len(latest)} companies) ===")
for c in cols:
    non_null = latest[c].notna().sum()
    print(f"  {c:35s} {non_null:3d}/{len(latest)}  ({100*non_null/len(latest):.0f}%)")

conn.close()
