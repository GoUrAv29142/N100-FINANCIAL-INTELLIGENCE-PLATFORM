"""
src/analytics/peer.py

Sprint 3, Day 18: Peer Percentile Rankings.

Computes PERCENT_RANK for 10 metrics within each of the 11 peer groups,
using each company's latest available year. D/E is inverted (lower D/E
= higher percentile, since less debt is better). Companies not in any
peer group are gracefully skipped (not an error).
"""

import sqlite3
from pathlib import Path

import pandas as pd

from src.logger import get_logger

log = get_logger(__name__)

DB_PATH = Path("db") / "nifty100.db"

# 10 metrics per spec Day 18. D/E is inverted.
PEER_METRICS = {
    "roe": ("return_on_equity_pct", False),
    "roce": ("return_on_capital_employed_pct", False),
    "npm": ("net_profit_margin_pct", False),
    "de": ("debt_to_equity", True),
    "fcf": ("free_cash_flow_cr", False),
    "pat_cagr_5yr": ("pat_cagr_5yr", False),
    "revenue_cagr_5yr": ("revenue_cagr_5yr", False),
    "eps_cagr_5yr": ("eps_cagr_5yr", False),
    "interest_coverage": ("interest_coverage", False),
    "asset_turnover": ("asset_turnover", False),
}


def load_latest_ratios_with_peers() -> pd.DataFrame:
    """Load financial_ratios (latest year per company) joined with peer_groups."""
    conn = sqlite3.connect(DB_PATH)

    ratios = pd.read_sql_query("""
        SELECT * FROM financial_ratios
        WHERE (company_id, year) IN (
            SELECT company_id, MAX(year) FROM financial_ratios GROUP BY company_id
        )
    """, conn)

    peer_groups = pd.read_sql_query("SELECT company_id, peer_group_name FROM peer_groups", conn)
    conn.close()

    merged = ratios.merge(peer_groups, on="company_id", how="left")
    return merged


def compute_peer_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute percentile rank for each metric, within each peer group.
    Companies with peer_group_name == NaN (not in any group) are
    dropped here - they're reported separately by the caller.
    Returns a long-format DataFrame: company_id, peer_group_name,
    metric, value, percentile_rank, year.
    """
    grouped_rows = []

    in_groups = df[df["peer_group_name"].notna()]

    for group_name, group_df in in_groups.groupby("peer_group_name"):
        for metric_key, (col, invert) in PEER_METRICS.items():
            if col not in group_df.columns:
                continue

            valid = group_df[group_df[col].notna()]
            if len(valid) == 0:
                continue

            ranks = valid[col].rank(pct=True, method="average")
            if invert:
                ranks = 1 - ranks

            for idx, row in valid.iterrows():
                grouped_rows.append({
                    "company_id": row["company_id"],
                    "peer_group_name": group_name,
                    "metric": metric_key,
                    "value": row[col],
                    "percentile_rank": round(ranks.loc[idx], 4),
                    "year": row["year"],
                })

    return pd.DataFrame(grouped_rows)


def populate_peer_percentiles():
    """Compute and write peer_percentiles table to SQLite."""
    df = load_latest_ratios_with_peers()

    no_group = df[df["peer_group_name"].isna()]
    log.info("Companies with no peer group assigned: %d (%s)",
              len(no_group), ", ".join(sorted(no_group["company_id"].tolist())))

    percentiles = compute_peer_percentiles(df)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM peer_percentiles")
    conn.commit()
    percentiles.to_sql("peer_percentiles", conn, if_exists="append", index=False)
    conn.close()

    log.info("peer_percentiles table populated: %d rows across %d peer groups",
              len(percentiles), percentiles["peer_group_name"].nunique())

    return percentiles


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    result = populate_peer_percentiles()

    print(f"\nTotal rows: {len(result)}")
    print(f"Peer groups covered: {sorted(result['peer_group_name'].unique())}")

    print("\n=== Sanity check: IT Services highest ROE should have highest ROE percentile ===")
    it_roe = result[(result["peer_group_name"] == "IT Services") & (result["metric"] == "roe")]
    it_roe_sorted = it_roe.sort_values("value", ascending=False)
    print(it_roe_sorted[["company_id", "value", "percentile_rank"]].to_string(index=False))
    top_by_value = it_roe_sorted.iloc[0]["company_id"]
    top_by_pct = it_roe.sort_values("percentile_rank", ascending=False).iloc[0]["company_id"]
    print(f"\nHighest ROE company: {top_by_value} | Highest percentile company: {top_by_pct} | Match: {top_by_value == top_by_pct}")