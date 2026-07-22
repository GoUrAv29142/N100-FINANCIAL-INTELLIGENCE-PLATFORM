import pandas as pd

print("=== load_audit.csv ===")
audit = pd.read_csv(r"D:\nifty100-capstone\output\load_audit.csv")
print(audit.to_string())

print("\n=== validation_failures.csv ===")
failures = pd.read_csv(r"D:\nifty100-capstone\output\validation_failures.csv")
print(f"Total rows: {len(failures)}")
print(f"\nColumns: {list(failures.columns)}")

if "issue" in failures.columns:
    print("\nBreakdown by issue type:")
    print(failures["issue"].value_counts())
elif "severity" in failures.columns:
    print("\nBreakdown by severity:")
    print(failures["severity"].value_counts())

print("\nFirst 20 rows:")
print(failures.head(20).to_string())