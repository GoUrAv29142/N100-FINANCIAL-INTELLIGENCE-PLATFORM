import sqlite3

conn = sqlite3.connect('db/nifty100.db')
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print(f"{len(tables)} tables found:")
for t in tables:
    print(f"  - {t}")
conn.close()
