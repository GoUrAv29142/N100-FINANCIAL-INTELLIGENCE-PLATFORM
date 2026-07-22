import pandas as pd

df = pd.read_excel(r"D:\nifty100-capstone\data\raw\core\financial_ratios.xlsx", sheet_name="Sheet1", header=0)
df["company_id"] = df["company_id"].astype(str).str.strip().str.upper()

dupe_mask = df.duplicated(subset=["company_id", "year"], keep=False)
dupes = df[dupe_mask].sort_values(["company_id", "year"])

print(f"Total rows: {len(df)}")
print(f"Rows involved in duplicate company_id+year groups: {len(dupes)}")

# Check: are duplicate rows byte-identical, or do values differ?
identical_count = 0
differing_count = 0
for (cid, yr), group in dupes.groupby(["company_id", "year"]):
    if group.drop(columns=["company_id", "year"]).nunique().sum() == 0:
        identical_count += 1
    else:
        differing_count += 1

print(f"\nDuplicate groups that are fully identical: {identical_count}")
print(f"Duplicate groups with DIFFERING values: {differing_count}")

# Show a sample of differing ones if any exist
if differing_count > 0:
    print("\nSample of a differing duplicate group:")
    for (cid, yr), group in dupes.groupby(["company_id", "year"]):
        if group.drop(columns=["company_id", "year"]).nunique().sum() > 0:
            print(group.to_string())
            break