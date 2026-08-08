"""
Day 29 (gap-fill) - CAGR Cross-Validator
Compares output/analysis_parsed.csv values against the Ratio Engine's
computed CAGR/ROE columns in financial_ratios, flagging divergence > 5%
for manual review. Writes output/cross_validation.csv (name per project
doc Module 9, section 9.5).

Judgment calls:
- compounded_sales_growth: compared to revenue_cagr_3yr or revenue_cagr_5yr
  depending on parsed period_years. Other periods (e.g. 10yr) have no
  computed equivalent in financial_ratios -> marked not_computed.
- compounded_profit_growth: compared to pat_cagr_5yr only (no 3yr PAT CAGR
  column exists). Other periods -> not_computed.
- stock_price_cagr: no computed equivalent anywhere in this pipeline
  (doc marks this field "display only, requires market_cap dataset") ->
  always not_computed.
- roe: parsed value is a multi-year average ("10 Years: 17%"), so it's
  compared against the mean of return_on_equity_pct over the last
  period_years AVAILABLE rows (not calendar-continuous), consistent with
  the "available years" convention used throughout Sprint 5.
- divergence_pct = abs(parsed - computed) / abs(computed) * 100, using
  the computed value as the denominator (matches doc wording: cross-check
  parsed value against Ratio Engine, not the reverse).
"""
import sqlite3
from pathlib import Path
import pandas as pd


def find_project_root(marker="db/nifty100.db"):
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / marker).exists():
            return current
        current = current.parent
    raise FileNotFoundError(f"Could not locate '{marker}' above {Path(__file__).resolve()}")


ROOT = find_project_root()
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"

DIVERGENCE_THRESHOLD = 5.0


def load_ratios(conn):
    return pd.read_sql(
        "SELECT company_id, CAST(year AS INTEGER) AS year, "
        "revenue_cagr_3yr, revenue_cagr_5yr, pat_cagr_5yr, return_on_equity_pct "
        "FROM financial_ratios",
        conn,
    )


def get_computed_value(row, ratio_hist):
    metric = row["metric_type"]
    period = row["period_years"]

    if ratio_hist.empty:
        return None, "no_ratio_data"

    latest = ratio_hist.iloc[-1]

    if metric == "compounded_sales_growth":
        if period == 3:
            val = latest["revenue_cagr_3yr"]
        elif period == 5:
            val = latest["revenue_cagr_5yr"]
        else:
            return None, "not_computed"
        return (val, "ok") if pd.notna(val) else (None, "computed_value_missing")

    if metric == "compounded_profit_growth":
        if period == 5:
            val = latest["pat_cagr_5yr"]
        else:
            return None, "not_computed"
        return (val, "ok") if pd.notna(val) else (None, "computed_value_missing")

    if metric == "stock_price_cagr":
        return None, "not_computed"

    if metric == "roe":
        tail = ratio_hist.tail(period) if len(ratio_hist) >= period else ratio_hist
        vals = tail["return_on_equity_pct"].dropna()
        if vals.empty:
            return None, "computed_value_missing"
        return vals.mean(), "ok"

    return None, "unknown_metric_type"


def main():
    conn = sqlite3.connect(DB_PATH)
    ratios = load_ratios(conn)
    conn.close()

    parsed = pd.read_csv(OUTPUT_DIR / "analysis_parsed.csv")

    records = []
    for _, row in parsed.iterrows():
        company_id = row["company_id"]
        ratio_hist = ratios[ratios["company_id"] == company_id].sort_values("year").reset_index(drop=True)
        computed_val, note = get_computed_value(row, ratio_hist)

        if computed_val is None:
            divergence_pct = None
            flagged = False
        else:
            if computed_val == 0:
                divergence_pct = None
                note = "computed_value_zero"
                flagged = False
            else:
                divergence_pct = round(abs(row["value_pct"] - computed_val) / abs(computed_val) * 100, 2)
                flagged = divergence_pct > DIVERGENCE_THRESHOLD

        records.append((
            company_id, row["metric_type"], row["period_years"], row["value_pct"],
            round(computed_val, 2) if computed_val is not None else None,
            divergence_pct, flagged, note,
        ))

    out_df = pd.DataFrame(records, columns=[
        "company_id", "metric_type", "period_years", "parsed_value_pct",
        "computed_value_pct", "divergence_pct", "flagged_for_review", "note",
    ])
    out_path = OUTPUT_DIR / "cross_validation.csv"
    out_df.to_csv(out_path, index=False)

    checked = out_df[out_df["note"] == "ok"]
    print(f"cross_validation.csv -> {out_path} ({len(out_df)} rows)")
    print(f"  Rows with a computed equivalent to check: {len(checked)}")
    print(f"  Rows flagged for review (divergence > {DIVERGENCE_THRESHOLD}%): {out_df['flagged_for_review'].sum()}")
    print("\nBreakdown by note:")
    print(out_df["note"].value_counts().to_string())
    if out_df["flagged_for_review"].sum() > 0:
        print("\nFlagged rows:")
        print(out_df[out_df["flagged_for_review"]].to_string(index=False))
    print("\nDone.")


if __name__ == "__main__":
    main()