import sqlite3
conn = sqlite3.connect(r"db\nifty100.db")
cur = conn.cursor()
cur.execute("PRAGMA table_info(financial_ratios)")
info = cur.fetchall()
cols = [r[1] for r in info]
print(f"financial_ratios has {len(cols)} columns:\n")
for c in cols:
    print(" ", c)

cagr_cols = [c for c in cols if "cagr" in c.lower()]
print("\nCAGR-related columns:", cagr_cols)

print("\nSample rows (first 3):")
cur.execute("SELECT * FROM financial_ratios LIMIT 3")
for row in cur.fetchall():
    print(dict(zip(cols, row)))
conn.close()
