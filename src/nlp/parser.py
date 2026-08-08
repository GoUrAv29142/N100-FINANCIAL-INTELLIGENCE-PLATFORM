"""
Day 29 - Analysis Text Parser
Parses growth/ROE text fields in data/raw/core/analysis.xlsx into
structured numeric records, then cross-validates the CAGR-type metrics
against the Ratio Engine's computed CAGR columns in financial_ratios.

Handles formatting found in the real source file:
  "10 Years: 21%"        -> period_years=10, value_pct=21.0
  "5 Years          14%" -> missing colon / extra spaces
  "1 Year: -2%"          -> negative values
  "TTM: 43%"             -> mapped to period_years=1
  "Last Year: 12%"       -> mapped to period_years=1
"""
import re
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE_XLSX = ROOT / "data" / "raw" / "core" / "analysis.xlsx"
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

METRIC_COLUMNS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]

CELL_PATTERN = re.compile(
    r'(\d+\s*Years?|TTM|Last\s*Year)\s*:?\s*(-?[\d.]+)\s*%',
    re.IGNORECASE,
)

# Only these combinations have a matching computed CAGR column in
# financial_ratios. stock_price_cagr has no computed equivalent at all,
# and roe is an average-over-period figure rather than a CAGR, so both
# are logged separately instead of being flagged as divergent.
METRIC_TO_COMPUTED_COL = {
    ("compounded_sales_growth", 3): "revenue_cagr_3yr",
    ("compounded_sales_growth", 5): "revenue_cagr_5yr",
    ("compounded_profit_growth", 5): "pat_cagr_5yr",
}
DIVERGENCE_THRESHOLD_PCT_POINTS = 5.0


def normalize_period(period_text: str):
    text = period_text.strip().lower()
    if "ttm" in text or "last year" in text:
        return 1
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def parse_cell(raw_value):
    if pd.isna(raw_value):
        return None, None
    match = CELL_PATTERN.search(str(raw_value))
    if not match:
        return None, None
    return normalize_period(match.group(1)), float(match.group(2))


def parse_analysis_file():
    df = pd.read_excel(SOURCE_XLSX, header=1)
    n_companies = df["company_id"].nunique()
    print(f"Loaded {len(df)} rows, {n_companies} unique companies")
    print(f"Companies present: {sorted(df['company_id'].unique().tolist())}\n")

    parsed_rows = []
    failure_rows = []

    for _, row in df.iterrows():
        company_id = row["company_id"]
        for metric in METRIC_COLUMNS:
            raw_value = row[metric]
            period, value = parse_cell(raw_value)
            if period is None:
                if pd.notna(raw_value):
                    failure_rows.append({
                        "company_id": company_id,
                        "metric_type": metric,
                        "raw_text": raw_value,
                    })
                continue
            parsed_rows.append({
                "company_id": company_id,
                "metric_type": metric,
                "period_years": period,
                "value_pct": value,
            })

    parsed_df = pd.DataFrame(
        parsed_rows,
        columns=["company_id", "metric_type", "period_years", "value_pct"],
    )
    failures_df = pd.DataFrame(
        failure_rows,
        columns=["company_id", "metric_type", "raw_text"],
    )

    parsed_path = OUTPUT_DIR / "analysis_parsed.csv"
    failures_path = OUTPUT_DIR / "parse_failures.csv"
    parsed_df.to_csv(parsed_path, index=False)
    failures_df.to_csv(failures_path, index=False)

    print(f"Parsed rows written : {len(parsed_df)} -> {parsed_path}")
    print(f"Parse failures       : {len(failures_df)} -> {failures_path}")
    if not failures_df.empty:
        print("\nSample failures:")
        print(failures_df.head(10).to_string(index=False))

    return parsed_df


def cross_validate(parsed_df: pd.DataFrame):
    conn = sqlite3.connect(DB_PATH)
    ratios = pd.read_sql(
        "SELECT company_id, CAST(year AS INTEGER) AS year, "
        "revenue_cagr_3yr, revenue_cagr_5yr, pat_cagr_5yr "
        "FROM financial_ratios",
        conn,
    )
    conn.close()

    latest = (
        ratios.sort_values("year")
        .groupby("company_id")
        .tail(1)
        .set_index("company_id")
    )

    validated_rows = []
    unvalidated_rows = []

    for _, row in parsed_df.iterrows():
        key = (row["metric_type"], int(row["period_years"]))
        company_id = row["company_id"]

        if key not in METRIC_TO_COMPUTED_COL:
            if row["metric_type"] == "stock_price_cagr":
                reason = "no computed equivalent in financial_ratios"
            elif row["metric_type"] == "roe":
                reason = "roe is an average-over-period figure, not a CAGR"
            else:
                reason = f"no {row['period_years']}yr computed CAGR for this metric"
            unvalidated_rows.append({**row.to_dict(), "reason": reason})
            continue

        if company_id not in latest.index:
            unvalidated_rows.append({**row.to_dict(), "reason": "company not found in financial_ratios"})
            continue

        computed_value = latest.loc[company_id, METRIC_TO_COMPUTED_COL[key]]
        if pd.isna(computed_value):
            unvalidated_rows.append({**row.to_dict(), "reason": f"{METRIC_TO_COMPUTED_COL[key]} is null for latest year"})
            continue

        divergence = abs(row["value_pct"] - computed_value)
        validated_rows.append({
            "company_id": company_id,
            "metric_type": row["metric_type"],
            "period_years": row["period_years"],
            "parsed_value_pct": row["value_pct"],
            "computed_value_pct": round(float(computed_value), 2),
            "divergence_pct_points": round(divergence, 2),
            "flagged": divergence > DIVERGENCE_THRESHOLD_PCT_POINTS,
        })

    validated_df = pd.DataFrame(validated_rows)
    unvalidated_df = pd.DataFrame(unvalidated_rows)

    out_path = OUTPUT_DIR / "cagr_cross_validation.csv"
    validated_df.to_csv(out_path, index=False)

    print(f"\n{'='*60}")
    print("CROSS-VALIDATION vs financial_ratios (latest year per company)")
    print(f"{'='*60}")
    print(f"Validated combinations : {len(validated_df)} -> {out_path}")
    print(f"Not validatable        : {len(unvalidated_df)} (see reasons below)")
    if not unvalidated_df.empty:
        print("\nReasons breakdown:")
        print(unvalidated_df["reason"].value_counts().to_string())
    if not validated_df.empty:
        flagged = validated_df[validated_df["flagged"]]
        print(f"\nFlagged for manual review (>{DIVERGENCE_THRESHOLD_PCT_POINTS} pct-point divergence): {len(flagged)}")
        if not flagged.empty:
            print(flagged.to_string(index=False))
        else:
            print("None - all validated values are within tolerance.")


def main():
    parsed_df = parse_analysis_file()
    cross_validate(parsed_df)
    print("\nDone.")


if __name__ == "__main__":
    main()
