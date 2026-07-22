import sqlite3
import pandas as pd

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

companies_to_check = ["ABB", "TCS", "INFY"]

for cid in companies_to_check:
    print(f"\n=== {cid} ===")
    pnl = pd.read_sql(f"SELECT year, net_profit, sales FROM profitandloss WHERE company_id='{cid}' ORDER BY year", conn)
    bs = pd.read_sql(f"SELECT year, equity_capital, reserves FROM balancesheet WHERE company_id='{cid}' ORDER BY year", conn)
    fr = pd.read_sql(f"SELECT year, return_on_equity_pct, revenue_cagr_5yr FROM financial_ratios WHERE company_id='{cid}' ORDER BY year", conn)

    print("P&L:\n", pnl.to_string())
    print("\nBS:\n", bs.to_string())
    print("\nfinancial_ratios (computed):\n", fr.to_string())

conn.close()