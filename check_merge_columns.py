import sys
sys.path.insert(0, r"D:\nifty100-capstone")
from src.analytics.engine import load_data, calculate_ratios

tables = load_data()
merged = calculate_ratios(tables)

target_cols = ["market_cap_crore", "enterprise_value_crore", "pe_ratio", "pb_ratio", "ev_ebitda", "dividend_yield_pct"]
for col in target_cols:
    present = col in merged.columns
    print(f"{col}: present={present}")
    if present:
        print(f"  non-null count: {merged[col].notna().sum()} / {len(merged)}")

# Also print any column with _mc suffix in case of collision renaming
mc_suffixed = [c for c in merged.columns if c.endswith("_mc")]
print(f"\nColumns with _mc suffix (renamed due to name collision): {mc_suffixed}")