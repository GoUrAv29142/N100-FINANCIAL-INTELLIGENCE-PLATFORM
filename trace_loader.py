import sys
sys.path.insert(0, r"D:\nifty100-capstone")

from src.etl.loader import read_raw_sheet, clean_companies, clean_table, _filter_to_known_companies, _deduplicate

TABLE = "profitandloss"  # change to balancesheet / cashflow to check those too

# Stage 0: raw read
raw = read_raw_sheet(TABLE)
print(f"Stage 0 - raw read: {len(raw)} rows")

# Get valid company ids
raw_companies = read_raw_sheet("companies")
companies = clean_companies(raw_companies)
valid_ids = set(companies["id"])
print(f"Valid company ids: {len(valid_ids)}")

# Stage 1: after normalize + dropna
cleaned = clean_table(TABLE, raw)
print(f"Stage 1 - after normalize/dropna: {len(cleaned)} rows  (lost: {len(raw) - len(cleaned)})")

# Stage 2: after filtering to known companies
filtered = _filter_to_known_companies(TABLE, cleaned, valid_ids)
print(f"Stage 2 - after company filter: {len(filtered)} rows  (lost: {len(cleaned) - len(filtered)})")

# Stage 3: after dedup
deduped = _deduplicate(TABLE, filtered, key_cols=["company_id", "year"])
print(f"Stage 3 - after dedup: {len(deduped)} rows  (lost: {len(filtered) - len(deduped)})")

print(f"\nTOTAL LOST: {len(raw) - len(deduped)} out of {len(raw)}")

# If stage 2 is the culprit, show which company_ids got rejected
if len(cleaned) - len(filtered) > 0:
    rejected_ids = set(cleaned["company_id"]) - valid_ids
    print(f"\ncompany_ids in {TABLE} but NOT in companies table ({len(rejected_ids)} unique):")
    for cid in sorted(rejected_ids):
        count = (cleaned["company_id"] == cid).sum()
        print(f"  {cid}: {count} rows")

# If stage 1 is the culprit, show sample of what got dropped
if len(raw) - len(cleaned) > 0:
    print(f"\nSample raw rows that failed normalization (check company_id/year values):")
    merged_check = raw.copy()
    merged_check["_kept"] = merged_check.index.isin(cleaned.index)
    print(merged_check[~merged_check["_kept"]][["company_id", "year"]].head(20))