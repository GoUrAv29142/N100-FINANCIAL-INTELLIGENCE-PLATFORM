import pandas as pd
pd.set_option("display.max_colwidth", None)
df = pd.read_excel(r"data\raw\core\analysis.xlsx")
print("Columns:", list(df.columns))
print("Shape:", df.shape)
print()
print(df.head(5).to_string())
