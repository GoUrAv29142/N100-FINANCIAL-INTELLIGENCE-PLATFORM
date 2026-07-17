"""
scripts/manual_review.py

Day 06: pulls every row for a given ticker across all tables in
nifty100.db, so you can manually compare it against the source Excel.

Usage:
    python -m scripts.manual_review TCS
    python -m scripts.manual_review RELIANCE
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

DB_PATH = Path("db") / "nifty100.db"

TABLES_WITH_COMPANY_ID = [
    "profitandloss", "balancesheet", "cashflow", "analysis",
    "documents", "prosandcons", "sectors", "stock_prices",
    "financial_ratios", "peer_groups",
]


def trace_company(ticker: str) -> None:
    conn = sqlite3.connect(DB_PATH)

    print("=" * 80)
    print(f"COMPANY: {ticker}")
    print("=" * 80)

    company = pd.read_sql(
        "SELECT * FROM companies WHERE id = ?", conn, params=(ticker,)
    )
    if company.empty:
        print(f"\n*** '{ticker}' not found in companies table. ***")
        conn.close()
        return

    print("\n--- companies ---")
    print(company.to_string(index=False))

    for table in TABLES_WITH_COMPANY_ID:
        df = pd.read_sql(
            f"SELECT * FROM {table} WHERE company_id = ? ORDER BY 1",
            conn, params=(ticker,)
        )
        print(f"\n--- {table} ({len(df)} rows) ---")
        if df.empty:
            print("  (no rows)")
        else:
            # stock_prices can be huge — just show first/last 3 rows
            if table == "stock_prices" and len(df) > 6:
                print(pd.concat([df.head(3), df.tail(3)]).to_string(index=False))
            else:
                print(df.to_string(index=False))

    conn.close()


def year_coverage_summary() -> None:
    """Bonus: show every company's P&L year coverage, flag <5 years."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT company_id, COUNT(DISTINCT year) AS n_years "
        "FROM profitandloss GROUP BY company_id ORDER BY n_years ASC",
        conn
    )
    conn.close()

    thin = df[df["n_years"] < 5]
    print("\n" + "=" * 80)
    print(f"YEAR COVERAGE: {len(thin)} companies with < 5 years of P&L data")
    print("=" * 80)
    print(thin.to_string(index=False) if not thin.empty else "  (none)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.manual_review <TICKER>")
        print("\nShowing year-coverage summary instead:\n")
        year_coverage_summary()
    else:
        trace_company(sys.argv[1].upper())