import pandas as pd

df = pd.read_excel(r"D:\nifty100-capstone\data\raw\core\financial_ratios.xlsx", sheet_name="Sheet1", header=0)
df["company_id"] = df["company_id"].astype(str).str.strip().str.upper()

dupe_mask = df.duplicated(subset=["company_id", "year"], keep=False)
dupes = df[dupe_mask].sort_values(["company_id", "year"])

cf_cols = ["free_cash_flow_cr", "capex_cr", "cash_from_operations_cr"]

first_is_better = 0
second_is_better = 0
same_completeness = 0

for (cid, yr), group in dupes.groupby(["company_id", "year"]):
    group = group.reset_index(drop=True)
    if len(group) != 2:
        continue  # only handle simple 2-row dupes for this check
    row1_nulls = group.loc[0, cf_cols].isna().sum() + (group.loc[0, cf_cols] == 0).sum()
    row2_nulls = group.loc[1, cf_cols].isna().sum() + (group.loc[1, cf_cols] == 0).sum()
    if row1_nulls < row2_nulls:
        first_is_better += 1
    elif row2_nulls < row1_nulls:
        second_is_better += 1
    else:
        same_completeness += 1

print(f"Groups where FIRST row is more complete: {first_is_better}")
print(f"Groups where SECOND row is more complete: {second_is_better}")
print(f"Groups with same completeness: {same_completeness}")