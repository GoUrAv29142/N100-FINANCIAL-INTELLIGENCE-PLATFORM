import sqlite3
import pandas as pd

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("All tables in database:", [t[0] for t in tables])

# Does a standalone market_cap table exist?
if any(t[0] == 'market_cap' for t in tables):
    df = pd.read_sql("SELECT * FROM market_cap LIMIT 5", conn)
    print("\nmarket_cap table columns:", list(df.columns))
    print(df.to_string())
else:
    print("\nNo standalone 'market_cap' table exists in the database.")

conn.close()