import sqlite3
conn = sqlite3.connect(r"db\nifty100.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("All tables:", tables)

for tbl in ("companies", "sectors"):
    if tbl in tables:
        cur.execute(f"PRAGMA table_info({tbl})")
        cols = [r[1] for r in cur.fetchall()]
        print(f"\n{tbl} columns:", cols)
        cur.execute(f"SELECT * FROM {tbl} LIMIT 5")
        for row in cur.fetchall():
            print(" ", dict(zip(cols, row)))
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        print(f"{tbl} row count:", cur.fetchone()[0])
    else:
        print(f"\n(no '{tbl}' table)")

conn.close()
