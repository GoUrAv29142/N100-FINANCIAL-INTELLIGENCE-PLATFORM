import sqlite3

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")
cursor = conn.execute("PRAGMA table_info(financial_ratios);")
print("=== financial_ratios columns ===")
for row in cursor.fetchall():
    print(row)

print("\n=== Row count ===")
count = conn.execute("SELECT COUNT(*) FROM financial_ratios;").fetchone()
print(count[0])

print("\n=== Sample row ===")
sample = conn.execute("SELECT * FROM financial_ratios LIMIT 1;").fetchone()
print(sample)

conn.close()