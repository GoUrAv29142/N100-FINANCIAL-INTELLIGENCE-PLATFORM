import sqlite3
import pandas as pd

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

print("=== peer_groups table ===")
pg = pd.read_sql("SELECT * FROM peer_groups LIMIT 10", conn)
print(pg.to_string())
print(f"\nTotal rows: {pd.read_sql('SELECT COUNT(*) as n FROM peer_groups', conn).iloc[0]['n']}")
print(f"Distinct peer groups: {pd.read_sql('SELECT COUNT(DISTINCT peer_group_name) as n FROM peer_groups', conn).iloc[0]['n'] if 'peer_group_name' in pg.columns else 'column name unknown - see columns above'}")

print("\n=== Companies with NO peer group ===")
no_peer = pd.read_sql("""
    SELECT c.id FROM companies c
    LEFT JOIN peer_groups p ON c.id = p.company_id
    WHERE p.company_id IS NULL
""", conn)
print(f"Count: {len(no_peer)}")

conn.close()