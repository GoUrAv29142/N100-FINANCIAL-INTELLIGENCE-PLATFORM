import sqlite3
import pandas as pd

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

df = pd.read_sql("SELECT * FROM sectors LIMIT 5", conn)
print(df.to_string())

print("\nDistinct broad_sector values:")
print(pd.read_sql("SELECT DISTINCT broad_sector FROM sectors", conn))

print("\nFinancials count:")
print(conn.execute("SELECT COUNT(*) FROM sectors WHERE broad_sector = 'Financials'").fetchone())

conn.close()