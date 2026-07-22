import pandas as pd
import sqlite3

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

files = {
    "profitandloss": r"D:\nifty100-capstone\data\raw\core\profitandloss.xlsx",
    "balancesheet":  r"D:\nifty100-capstone\data\raw\core\balancesheet.xlsx",
    "cashflow":      r"D:\nifty100-capstone\data\raw\core\cashflow.xlsx",
}

for table, path in files.items():
    raw = pd.read_excel(path, header=1)  # per spec: core files use header=1
    loaded = pd.read_sql(f"SELECT COUNT(*) as n FROM {table}", conn).iloc[0]["n"]
    print(f"{table}: raw Excel = {len(raw)} rows | loaded in SQLite = {loaded} rows | dropped = {len(raw) - loaded}")

conn.close()
