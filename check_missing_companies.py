import pandas as pd

df = pd.read_excel(r"D:\nifty100-capstone\data\raw\core\companies.xlsx", sheet_name="Companies", header=1)
print(f"Total rows in companies.xlsx: {len(df)}")
print(f"Columns: {list(df.columns)}")

missing = ["ULTRACEMCO", "UNIONBANK", "UNITDSPR", "VBL", "VEDL", "WIPRO", "ZOMATO", "ZYDUSLIFE"]

for ticker in missing:
    match = df[df["id"].astype(str).str.strip().str.upper() == ticker]
    if len(match) > 0:
        print(f"{ticker}: FOUND in raw file -> {match['id'].values}")
    else:
        print(f"{ticker}: NOT in raw file at all")

# Also print the actual raw id values in case of whitespace/casing issues
print(f"\nTotal unique ids in raw file: {df['id'].nunique()}")
print(f"Sample raw id values:\n{df['id'].head(20).tolist()}")