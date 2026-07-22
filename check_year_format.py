import sqlite3

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

tables = ["profitandloss", "balancesheet", "cashflow", "financial_ratios"]

for t in tables:
    print(f"\n=== {t} ===")
    rows = conn.execute(f"SELECT DISTINCT year FROM {t} ORDER BY year LIMIT 5;").fetchall()
    for r in rows:
        print(r)
    count = conn.execute(f"SELECT COUNT(DISTINCT company_id || '|' || year) FROM {t};").fetchone()
    print(f"Distinct company-year pairs: {count[0]}")

conn.close()