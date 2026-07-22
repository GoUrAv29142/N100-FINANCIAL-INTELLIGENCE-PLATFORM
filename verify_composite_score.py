import sqlite3
import pandas as pd

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

total = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
non_null = conn.execute("SELECT COUNT(composite_quality_score) FROM financial_ratios").fetchone()[0]
print(f"composite_quality_score: {non_null} / {total} non-null")

sample = pd.read_sql("""
    SELECT company_id, year, return_on_equity_pct, free_cash_flow_cr,
           return_on_capital_employed_pct, debt_to_equity, composite_quality_score
    FROM financial_ratios
    ORDER BY composite_quality_score DESC
    LIMIT 5
""", conn)
print("\nTop 5 by composite_quality_score:")
print(sample.to_string())

sample2 = pd.read_sql("""
    SELECT company_id, year, composite_quality_score
    FROM financial_ratios
    WHERE composite_quality_score IS NOT NULL
    ORDER BY composite_quality_score ASC
    LIMIT 5
""", conn)
print("\nBottom 5 by composite_quality_score:")
print(sample2.to_string())

stats = pd.read_sql("SELECT MIN(composite_quality_score) as min_val, MAX(composite_quality_score) as max_val, AVG(composite_quality_score) as avg_val FROM financial_ratios", conn)
print("\nRange check (should be roughly 0-100):")
print(stats.to_string())

conn.close()