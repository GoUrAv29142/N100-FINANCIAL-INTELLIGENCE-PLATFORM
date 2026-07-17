from src.etl.loader import load_all_raw

tables = load_all_raw()

print("\n=== DUPLICATE COUNTS ===")
for name in ["profitandloss", "balancesheet", "cashflow", "financial_ratios"]:
    df = tables.get(name)
    if df is not None and {"company_id", "year"}.issubset(df.columns):
        dup = df[df.duplicated(["company_id", "year"], keep=False)]
        print(f"{name}: {len(dup)}")

print("\n=== SAMPLE DUPLICATES FROM PROFITANDLOSS ===")
dup = tables["profitandloss"][
    tables["profitandloss"].duplicated(
        ["company_id", "year"],
        keep=False
    )
]

if len(dup):
    print(dup[["company_id", "year"]].head(30))
else:
    print("No duplicates found.")