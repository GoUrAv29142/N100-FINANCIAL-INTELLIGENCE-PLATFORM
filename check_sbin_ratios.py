import sqlite3
from pathlib import Path

conn = sqlite3.connect("db/nifty100.db")

count = conn.execute(
    "SELECT COUNT(*) FROM financial_ratios WHERE company_id = 'SBIN'"
).fetchone()[0]
print(f"SBIN financial_ratios rows: {count}")

if count > 0:
    import pandas as pd
    df = pd.read_sql(
        "SELECT year, return_on_equity_pct, debt_to_equity, "
        "return_on_capital_employed_pct, revenue_cagr_5yr, pat_cagr_5yr "
        "FROM financial_ratios WHERE company_id = 'SBIN' ORDER BY year",
        conn,
    )
    print(df.to_string(index=False))
else:
    print("No rows found - ratios.py either didn't process SBIN, or overwrote/skipped it.")
    total = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    print(f"Total financial_ratios rows in DB (all companies): {total}")

conn.close()