import sqlite3

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

for t in ["profitandloss", "balancesheet"]:
    before = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE year LIKE '%.0';").fetchone()[0]

    # Strip the trailing '.0' from year values
    conn.execute(f"""
        UPDATE {t}
        SET year = SUBSTR(year, 1, LENGTH(year) - 2)
        WHERE year LIKE '%.0';
    """)
    conn.commit()

    after = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE year LIKE '%.0';").fetchone()[0]
    print(f"{t}: fixed {before} rows, {after} still have '.0' (should be 0)")

# Sanity check: print a few sample years post-fix
for t in ["profitandloss", "balancesheet"]:
    sample = conn.execute(f"SELECT DISTINCT year FROM {t} ORDER BY year LIMIT 5;").fetchall()
    print(f"\n{t} sample years after fix:", sample)

conn.close()