import sqlite3
import os

db_path = os.path.join(os.getcwd(), "db", "nifty100.db")
schema_path = os.path.join(os.getcwd(), "db", "schema.sql")

print(f"DB path: {db_path}")
print(f"Schema path: {schema_path}")
print(f"Schema file exists: {os.path.exists(schema_path)}")

conn = sqlite3.connect(db_path)
with open(schema_path, "r") as f:
    conn.executescript(f.read())
conn.commit()

tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print(f"\n{len(tables)} tables found:")
for t in tables:
    print(f"  - {t}")

conn.close()

print(f"\nDB file size: {os.path.getsize(db_path)} bytes")