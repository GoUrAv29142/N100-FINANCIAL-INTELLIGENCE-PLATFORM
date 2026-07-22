import sqlite3

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

# Check if ANY '2011.0'-style values exist in pnl/bs
for t in ["profitandloss", "balancesheet"]:
    bad = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE year LIKE '%.0';").fetchone()
    total = conn.execute(f"SELECT COUNT(*) FROM {t};").fetchone()
    print(f"{t}: {bad[0]} / {total[0]} rows have '.0' suffix")

conn.close()