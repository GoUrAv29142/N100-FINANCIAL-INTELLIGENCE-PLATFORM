import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "nifty100.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def load_data(db_path: str = DB_PATH) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        companies = pd.read_sql("SELECT id, company_name FROM companies", conn)
        sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
        ratios = pd.read_sql("SELECT * FROM financial_ratios", conn)
    finally:
        conn.close()

    companies["company_name"] = companies["company_name"].astype(str).str.split("\n").str[0].str.strip()
    df = ratios.merge(companies, left_on="company_id", right_on="id", how="left")
    df = df.merge(sectors, on="company_id", how="left")
    return df


def latest_year_snapshot(df: pd.DataFrame, db_path: str = DB_PATH) -> pd.DataFrame:
    valuation_rows = df.dropna(subset=["market_cap_crore"])
    if valuation_rows.empty:
        raise ValueError("No rows with market_cap_crore found — cannot compute valuation.")
    idx = valuation_rows.groupby("company_id")["year"].idxmax()
    snap = valuation_rows.loc[idx].copy()

    ids_with_ratios = set(df["company_id"].unique())
    ids_with_valuation = set(snap["company_id"].unique())
    missing_ids = ids_with_ratios - ids_with_valuation
    if missing_ids:
        idx_latest = df[df["company_id"].isin(missing_ids)].groupby("company_id")["year"].idxmax()
        fallback = df.loc[idx_latest].copy()
        snap = pd.concat([snap, fallback], ignore_index=True)

    conn = sqlite3.connect(db_path)
    try:
        all_ids = pd.read_sql("SELECT id AS company_id, company_name FROM companies", conn)
        sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    finally:
        conn.close()
    all_ids["company_name"] = all_ids["company_name"].astype(str).str.split("\n").str[0].str.strip()

    fully_missing = set(all_ids["company_id"]) - set(snap["company_id"].unique())
    if fully_missing:
        stub_cols = snap.columns
        stub = pd.DataFrame({"company_id": list(fully_missing)})
        stub = stub.merge(all_ids, on="company_id", how="left")
        stub = stub.merge(sectors, on="company_id", how="left")
        for col in stub_cols:
            if col not in stub.columns:
                stub[col] = pd.NA
        stub = stub[stub_cols]
        snap = pd.concat([snap, stub], ignore_index=True)

    return snap


def compute_fcf_yield(snap: pd.DataFrame) -> pd.DataFrame:
    snap = snap.copy()
    snap["FCF_yield_pct"] = None
    valid = snap["market_cap_crore"].notna() & (snap["market_cap_crore"] != 0) & snap["free_cash_flow_cr"].notna()
    snap.loc[valid, "FCF_yield_pct"] = (
        snap.loc[valid, "free_cash_flow_cr"] / snap.loc[valid, "market_cap_crore"] * 100
    ).round(2)
    return snap


def compute_5yr_median_pe(df: pd.DataFrame, snap: pd.DataFrame) -> pd.DataFrame:
    pe_hist = df.dropna(subset=["pe_ratio"])
    median_pe = pe_hist.groupby("company_id")["pe_ratio"].median().rename("5yr_median_PE").round(2)
    return snap.merge(median_pe, on="company_id", how="left")


def compute_sector_median_pe(snap: pd.DataFrame) -> pd.DataFrame:
    sector_median = snap.groupby("broad_sector")["pe_ratio"].median().rename("sector_median_pe")
    snap = snap.merge(sector_median, on="broad_sector", how="left")
    return snap


def apply_overvaluation_flag(snap: pd.DataFrame) -> pd.DataFrame:
    snap = snap.copy()

    def flag_row(r):
        pe = r["pe_ratio"]
        smed = r["sector_median_pe"]
        if pd.isna(pe) or pd.isna(smed) or smed == 0:
            return "N/A"
        if pe > smed * 1.5:
            return "Caution"
        if pe < smed * 0.7:
            return "Discount"
        return "Fair"

    snap["flag"] = snap.apply(flag_row, axis=1)

    def pct_vs_sector(r):
        pe, smed = r["pe_ratio"], r["sector_median_pe"]
        if pd.isna(pe) or pd.isna(smed) or smed == 0:
            return None
        return round((pe - smed) / smed * 100, 1)

    snap["PE_vs_sector_median_pct"] = snap.apply(pct_vs_sector, axis=1)
    return snap


def build_valuation_summary(db_path: str = DB_PATH) -> pd.DataFrame:
    df = load_data(db_path)
    snap = latest_year_snapshot(df, db_path)
    snap = compute_fcf_yield(snap)
    snap = compute_5yr_median_pe(df, snap)
    snap = compute_sector_median_pe(snap)
    snap = apply_overvaluation_flag(snap)

    out = snap.rename(columns={
        "broad_sector": "sector",
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "ev_ebitda": "EV/EBITDA",
        "sector_median_pe": "sector_median_pe_for_reference",
    })[[
        "company_id", "company_name", "sector", "P/E", "P/B", "EV/EBITDA",
        "FCF_yield_pct", "5yr_median_PE", "PE_vs_sector_median_pct", "flag",
    ]].sort_values("company_id").reset_index(drop=True)

    return out


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    summary = build_valuation_summary()

    xlsx_path = os.path.join(OUTPUT_DIR, "valuation_summary.xlsx")
    summary.to_excel(xlsx_path, index=False, sheet_name="Valuation Summary")

    flags = summary[summary["flag"].isin(["Caution", "Discount"])].copy()
    csv_path = os.path.join(OUTPUT_DIR, "valuation_flags.csv")
    flags.to_csv(csv_path, index=False)

    print(f"valuation_summary.xlsx: {len(summary)} rows -> {xlsx_path}")
    print(f"valuation_flags.csv:    {len(flags)} rows -> {csv_path}")
    print(summary["flag"].value_counts())


if __name__ == "__main__":
    main()