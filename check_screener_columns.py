import sqlite3

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")
cols = conn.execute("PRAGMA table_info(financial_ratios);").fetchall()
for c in cols:
    print(c)

conn.close()