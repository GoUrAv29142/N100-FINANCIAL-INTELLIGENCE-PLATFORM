import pandas as pd

df = pd.read_excel(r"D:\nifty100-capstone\data\raw\core\market_cap.xlsx", sheet_name="Sheet1", header=0)
print("Columns:", list(df.columns))
print(f"Rows: {len(df)}")
print(df.head().to_string())