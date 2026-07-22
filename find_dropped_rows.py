import sqlite3
import pandas as pd

conn = sqlite3.connect(r"D:\nifty100-capstone\db\nifty100.db")

pnl = pd.read_sql("SELECT DISTINCT company_id, year FROM profitandloss", conn)
bs  = pd.read_sql("SELECT DISTINCT company_id, year FROM balancesheet", conn)
cf  = pd.read_sql("SELECT DISTINCT company_id, year FROM cashflow", conn)

pnl["key"] = pnl.company_id + "|" + pnl.year
bs["key"]  = bs.company_id + "|" + bs.year
cf["key"]  = cf.company_id + "|" + cf.year

print(f"P&L: {len(pnl)}  BS: {len(bs)}  CF: {len(cf)}")

union_keys = set(pnl.key) | set(bs.key) | set(cf.key)
intersect_keys = set(pnl.key) & set(bs.key) & set(cf.key)
print(f"Union: {len(union_keys)}  Intersection: {len(intersect_keys)}")

# Which keys are in P&L+BS but missing from CF specifically?
pnl_bs = set(pnl.key) & set(bs.key)
missing_from_cf = pnl_bs - set(cf.key)
print(f"\nIn both P&L and BS but missing from CF: {len(missing_from_cf)}")

# Which keys are in CF but missing from P&L or BS?
missing_from_pnl = (set(bs.key) & set(cf.key)) - set(pnl.key)
missing_from_bs  = (set(pnl.key) & set(cf.key)) - set(bs.key)
print(f"In BS+CF but missing from P&L: {len(missing_from_pnl)}")
print(f"In P&L+CF but missing from BS: {len(missing_from_bs)}")

# Show a sample of what's missing from CF (likely biggest bucket)
sample = sorted(missing_from_cf)[:15]
print("\nSample company-years missing from cashflow:")
for s in sample:
    print(" ", s)

conn.close()