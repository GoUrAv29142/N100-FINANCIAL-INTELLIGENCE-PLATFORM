import sqlite3
import pandas as pd

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

total = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
print(f"Total rows: {total}")

# Rows with null free_cash_flow_cr should be exactly the ones that had no CF match
null_fcf = conn.execute("SELECT COUNT(*) FROM financial_ratios WHERE free_cash_flow_cr IS NULL").fetchone()[0]
null_cfo = conn.execute("SELECT COUNT(*) FROM financial_ratios WHERE cash_from_operations_cr IS NULL").fetchone()[0]
print(f"Rows with null free_cash_flow_cr: {null_fcf}")
print(f"Rows with null cash_from_operations_cr: {null_cfo}")

# Sanity check: non-CF KPIs should still be populated for these rows
sample = pd.read_sql("""
    SELECT company_id, year, net_profit_margin_pct, return_on_equity_pct,
           free_cash_flow_cr, cash_from_operations_cr, composite_quality_score
    FROM financial_ratios
    WHERE free_cash_flow_cr IS NULL
    LIMIT 10
""", conn)
print("\nSample rows with null CF fields (should still have NPM/ROE/composite score):")
print(sample.to_string())

conn.close()