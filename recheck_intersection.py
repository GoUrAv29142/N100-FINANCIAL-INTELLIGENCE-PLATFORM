import sqlite3
import pandas as pd

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

q = """
SELECT p.company_id, p.year
FROM profitandloss p
INNER JOIN balancesheet b ON p.company_id = b.company_id AND p.year = b.year
INNER JOIN cashflow c ON p.company_id = c.company_id AND p.year = c.year
"""
result = pd.read_sql(q, conn)
print(f"New intersection (P&L ∩ BS ∩ CF) after year fix: {len(result)}")

conn.close()