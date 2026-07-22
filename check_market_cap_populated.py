import sqlite3

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

cols_to_check = ["market_cap_crore", "pe_ratio", "pb_ratio", "ev_ebitda", "dividend_yield_pct"]
total = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]

for col in cols_to_check:
    non_null = conn.execute(f"SELECT COUNT({col}) FROM financial_ratios").fetchone()[0]
    print(f"{col}: {non_null} / {total} non-null")

conn.close()