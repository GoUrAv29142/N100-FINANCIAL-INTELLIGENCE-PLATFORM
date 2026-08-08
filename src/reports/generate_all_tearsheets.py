"""
Day 34 - Batch Tearsheet Generation
Runs Day 33's generate_tearsheet() across all 92 companies. Skips
companies with < 3 years of P&L history (same threshold tearsheet.py
already enforces) and logs skips to output/skipped_tearsheets.csv.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sqlite3
import pandas as pd
from tearsheet import DB_PATH, OUTPUT_DIR, REPORTS_DIR, generate_tearsheet


def main():
    conn = sqlite3.connect(DB_PATH)
    companies = pd.read_sql("SELECT id AS company_id FROM companies", conn)
    pros_cons_df = pd.read_csv(OUTPUT_DIR / "pros_cons_generated.csv")
    cf_intel_df = pd.read_excel(OUTPUT_DIR / "cashflow_intelligence.xlsx")

    generated, skipped = [], []
    for ticker in companies["company_id"]:
        path, status = generate_tearsheet(ticker, conn, pros_cons_df, cf_intel_df)
        if status == "ok":
            generated.append((ticker, path.stat().st_size))
        else:
            skipped.append((ticker, status))

    conn.close()

    skipped_df = pd.DataFrame(skipped, columns=["company_id", "reason"])
    skipped_path = OUTPUT_DIR / "skipped_tearsheets.csv"
    skipped_df.to_csv(skipped_path, index=False)

    print(f"Generated: {len(generated)} tearsheets in {REPORTS_DIR}")
    print(f"Skipped: {len(skipped)} -> {skipped_path}")
    if skipped:
        print(skipped_df.to_string(index=False))

    under_30kb = [(t, round(s / 1024, 1)) for t, s in generated if s < 30 * 1024]
    if under_30kb:
        print(f"\nWARNING: {len(under_30kb)} tearsheets under 30KB: {under_30kb}")
    else:
        print("\nAll generated tearsheets are >= 30KB.")

    expected = 92 - len(skipped)
    actual_count = len(list(REPORTS_DIR.glob("*.pdf")))
    print(f"\nExit-criteria check:")
    print(f"  Expected PDF count (92 - {len(skipped)} skipped) = {expected}")
    print(f"  Actual PDF count on disk in reports/tearsheets/: {actual_count}")
    print("Done.")


if __name__ == "__main__":
    main()