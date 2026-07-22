import sqlite3
import pandas as pd

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

cols = ["book_value_per_share", "dividend_payout_ratio_pct", "total_debt_cr", "cash_from_operations_cr"]

for col in cols:
    total = conn.execute(f"SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    non_null = conn.execute(f"SELECT COUNT({col}) FROM financial_ratios").fetchone()[0]
    print(f"{col}: {non_null} / {total} non-null")

sample = pd.read_sql("SELECT company_id, year, book_value_per_share, dividend_payout_ratio_pct, total_debt_cr, cash_from_operations_cr FROM financial_ratios LIMIT 5", conn)
print("\nSample rows:")
print(sample.to_string())

conn.close()