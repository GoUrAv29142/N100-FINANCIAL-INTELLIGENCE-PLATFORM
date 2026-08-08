import sqlite3
conn = sqlite3.connect(r"db\nifty100.db")
cur = conn.cursor()
known = ["HDFCBANK", "INFY", "SBILIFE", "TCS", "WIPRO"]
cur.execute("SELECT DISTINCT company_id FROM financial_ratios")
present = {r[0] for r in cur.fetchall()}
print("Missing from financial_ratios:", [c for c in known if c not in present])
conn.close()
