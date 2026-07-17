import sqlite3
import pandas as pd
import re
import sys

conn = sqlite3.connect("db/nifty100.db")
with open("notebooks/exploratory_queries.sql") as f:
    content = f.read()

queries = re.findall(r'(SELECT.*?;)', content, re.DOTALL)

n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
print(f"--- Query {n} ---\n")
df = pd.read_sql(queries[n - 1], conn)
print(df.to_string(index=False))
conn.close()