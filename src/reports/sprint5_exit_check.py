"""
Day 35 - Sprint 5 Exit-Criteria Verification
Checks every Sprint 5 deliverable against the project doc's Definition of
Done in one pass, instead of re-verifying each script's output by hand.
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
REPORTS_DIR = ROOT / "reports"

results = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((label, status, detail))
    print(f"  [{status}] {label}" + (f" - {detail}" if detail else ""))


def main():
    conn = sqlite3.connect(DB_PATH)
    total_companies = pd.read_sql("SELECT COUNT(*) AS n FROM companies", conn).iloc[0]["n"]
    conn.close()

    print("=== pros_cons_generated.csv ===")
    pc = pd.read_csv(OUTPUT_DIR / "pros_cons_generated.csv")
    ids_with_pro = set(pc[pc["type"] == "pro"]["company_id"])
    ids_with_con = set(pc[pc["type"] == "con"]["company_id"])
    check("Every company has >=1 pro", len(ids_with_pro) >= total_companies,
          f"{len(ids_with_pro)}/{total_companies}")
    check("Every company has >=1 con", len(ids_with_con) >= total_companies,
          f"{len(ids_with_con)}/{total_companies}")

    print("\n=== cashflow_intelligence.xlsx ===")
    cf = pd.read_excel(OUTPUT_DIR / "cashflow_intelligence.xlsx")
    check("Row count == 92", len(cf) == total_companies, f"{len(cf)} rows")
    required_cols = {"company_id", "sector", "cfo_quality_score", "cfo_quality_label",
                      "capex_intensity_pct", "capex_label", "fcf_cagr_5yr",
                      "fcf_conversion_pct", "distress_flag", "deleveraging_flag",
                      "capital_allocation_label"}
    check("All required columns present", required_cols.issubset(cf.columns),
          f"missing: {required_cols - set(cf.columns)}" if not required_cols.issubset(cf.columns) else "")

    print("\n=== distress_alerts.csv ===")
    check("distress_alerts.csv exists", (OUTPUT_DIR / "distress_alerts.csv").exists())

    print("\n=== reports/tearsheets/ ===")
    tearsheets = list((REPORTS_DIR / "tearsheets").glob("*.pdf"))
    skipped = pd.read_csv(OUTPUT_DIR / "skipped_tearsheets.csv") if (OUTPUT_DIR / "skipped_tearsheets.csv").exists() else pd.DataFrame()
    expected_count = total_companies - len(skipped)
    check("Tearsheet count matches (92 - skipped)", len(tearsheets) == expected_count,
          f"{len(tearsheets)} found, {len(skipped)} skipped, expected {expected_count}")
    under_30kb = [p.name for p in tearsheets if p.stat().st_size < 30 * 1024]
    check("All tearsheets >= 30KB", len(under_30kb) == 0,
          f"under 30KB: {under_30kb}" if under_30kb else "")

    print("\n=== reports/sector/ ===")
    sector_pdfs = list((REPORTS_DIR / "sector").glob("*.pdf"))
    conn = sqlite3.connect(DB_PATH)
    distinct_sectors = pd.read_sql("SELECT DISTINCT broad_sector FROM sectors", conn).shape[0]
    conn.close()
    check("11 sector PDFs exist", len(sector_pdfs) == 11,
          f"found {len(sector_pdfs)} PDFs, {distinct_sectors} distinct broad_sector values in DB "
          f"(doc expects 11 sectors incl. Conglomerates - see retro note)")

    print("\n=== reports/portfolio/ ===")
    portfolio_path = REPORTS_DIR / "portfolio" / "portfolio_summary.pdf"
    check("portfolio_summary.pdf exists", portfolio_path.exists(),
          f"{portfolio_path.stat().st_size / 1024:.1f} KB" if portfolio_path.exists() else "")

    print("\n" + "=" * 50)
    fails = [r for r in results if r[1] == "FAIL"]
    print(f"SUMMARY: {len(results) - len(fails)}/{len(results)} checks passed")
    if fails:
        print("\nFailed checks:")
        for label, _, detail in fails:
            print(f"  - {label}: {detail}")
    else:
        print("All automated checks passed.")


if __name__ == "__main__":
    main()