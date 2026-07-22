import sqlite3
import pandas as pd

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

# Use latest year per company for the screener check
query = """
SELECT company_id, year, return_on_equity_pct, debt_to_equity
FROM financial_ratios
WHERE (company_id, year) IN (
    SELECT company_id, MAX(year) FROM financial_ratios GROUP BY company_id
)
AND return_on_equity_pct > 15
AND debt_to_equity < 1
ORDER BY return_on_equity_pct DESC
"""

result = pd.read_sql(query, conn)
print(f"Companies matching ROE>15% AND D/E<1 (latest year): {len(result)}")
print(result.to_string())

conn.close()