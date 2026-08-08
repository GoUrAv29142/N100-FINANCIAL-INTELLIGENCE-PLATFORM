"""
Day 32 - Capital Allocation Report
Verifies capital_allocation.csv (Sprint 2 output) for completeness across
all 92 companies, builds a latest-year pattern distribution summary, merges
the latest-year pattern label into cashflow_intelligence.xlsx (Day 31
output), and detects year-over-year pattern changes per company.

Judgment calls:
- "Complete for all 92 companies x all years" is checked against the raw
  cashflow table's (company_id, year) pairs, since the pattern is derived
  from CFO/CFI/CFF signs and can only exist where cashflow data exists.
  A company missing entirely, or missing specific years that DO have
  cashflow data, is flagged separately.
- "Latest year" per company = max year present in capital_allocation.csv
  for that company (not a fixed calendar year), consistent with earlier
  Sprint 5 scripts using "available years" rather than calendar-continuous
  history.
- pattern_changes.csv walks each company's rows in year order (available
  years only) and logs every transition where pattern_label differs from
  the previous available year, not just latest-vs-prior.
- cashflow_intelligence.xlsx's capital_allocation_label column is
  overwritten with this authoritative Sprint 2 label regardless of what
  Day 31 was run with (Day 31 already prefers this file when present, but
  this script makes it authoritative even if Day 31 ran before this file
  existed).
"""
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

CAP_ALLOC_PATH = OUTPUT_DIR / "capital_allocation.csv"
CASHFLOW_INTEL_PATH = OUTPUT_DIR / "cashflow_intelligence.xlsx"


def load_companies_and_cashflow_years(conn):
    companies = pd.read_sql("SELECT id AS company_id FROM companies", conn)
    cf_years = pd.read_sql(
        "SELECT DISTINCT company_id, CAST(year AS INTEGER) AS year FROM cashflow",
        conn,
    )
    return companies, cf_years


def verify_completeness(companies, cf_years, cap_alloc):
    all_ids = set(companies["company_id"])
    cap_ids = set(cap_alloc["company_id"])
    missing_companies = sorted(all_ids - cap_ids)

    # (company, year) pairs that have cashflow data but no pattern label
    cf_pairs = set(zip(cf_years["company_id"], cf_years["year"]))
    cap_pairs = set(zip(cap_alloc["company_id"], cap_alloc["year"]))
    missing_pairs = sorted(cf_pairs - cap_pairs)

    return missing_companies, missing_pairs


def latest_year_distribution(cap_alloc):
    latest = cap_alloc.sort_values("year").groupby("company_id").tail(1)
    dist = latest["pattern_label"].value_counts()
    return latest, dist


def build_pattern_changes(cap_alloc):
    records = []
    for company_id, g in cap_alloc.sort_values("year").groupby("company_id"):
        g = g.reset_index(drop=True)
        for i in range(1, len(g)):
            prev_label = g.loc[i - 1, "pattern_label"]
            curr_label = g.loc[i, "pattern_label"]
            if prev_label != curr_label:
                records.append((
                    company_id,
                    g.loc[i - 1, "year"],
                    g.loc[i, "year"],
                    prev_label,
                    curr_label,
                ))
    return pd.DataFrame(records, columns=[
        "company_id", "from_year", "to_year", "from_pattern", "to_pattern",
    ])


def update_cashflow_intelligence(latest_labels_map):
    if not CASHFLOW_INTEL_PATH.exists():
        print(f"  WARNING: {CASHFLOW_INTEL_PATH} not found - run Day 31 script first. Skipping merge.")
        return
    intel = pd.read_excel(CASHFLOW_INTEL_PATH)
    if "capital_allocation_label" not in intel.columns:
        intel["capital_allocation_label"] = "No Data"
    intel["capital_allocation_label"] = intel["company_id"].map(latest_labels_map).fillna(
        intel["capital_allocation_label"]
    )
    intel.to_excel(CASHFLOW_INTEL_PATH, index=False)
    print(f"  Updated capital_allocation_label column in {CASHFLOW_INTEL_PATH}")


def main():
    if not CAP_ALLOC_PATH.exists():
        raise FileNotFoundError(
            f"{CAP_ALLOC_PATH} not found. Copy capital_allocation.csv into "
            f"the output/ folder before running this script."
        )

    conn = sqlite3.connect(DB_PATH)
    companies, cf_years = load_companies_and_cashflow_years(conn)
    conn.close()

    cap_alloc = pd.read_csv(CAP_ALLOC_PATH)
    required_cols = {"company_id", "year", "pattern_label"}
    if not required_cols.issubset(cap_alloc.columns):
        raise ValueError(f"capital_allocation.csv missing required columns: {required_cols - set(cap_alloc.columns)}")

    # ---------- 1. Completeness check ----------
    missing_companies, missing_pairs = verify_completeness(companies, cf_years, cap_alloc)
    print("=== Completeness check ===")
    print(f"  Companies in companies table: {len(companies)}")
    print(f"  Companies present in capital_allocation.csv: {cap_alloc['company_id'].nunique()}")
    print(f"  Companies missing entirely: {len(missing_companies)} {missing_companies}")
    print(f"  (company, year) pairs with cashflow data but no pattern label: {len(missing_pairs)}")
    if missing_pairs:
        preview = missing_pairs[:15]
        print(f"    Sample: {preview}{' ...' if len(missing_pairs) > 15 else ''}")

    # ---------- 2. Latest-year distribution summary ----------
    latest, dist = latest_year_distribution(cap_alloc)
    print("\n=== Latest-year capital allocation pattern distribution ===")
    print(dist.to_string())
    dist_path = OUTPUT_DIR / "capital_allocation_distribution.csv"
    dist.rename("company_count").rename_axis("pattern_label").reset_index().to_csv(dist_path, index=False)
    print(f"  Saved -> {dist_path}")

    # ---------- 3. Merge into cashflow_intelligence.xlsx ----------
    print("\n=== Updating cashflow_intelligence.xlsx ===")
    latest_labels_map = dict(zip(latest["company_id"], latest["pattern_label"]))
    update_cashflow_intelligence(latest_labels_map)

    # ---------- 4. pattern_changes.csv ----------
    changes_df = build_pattern_changes(cap_alloc)
    changes_path = OUTPUT_DIR / "pattern_changes.csv"
    changes_df.to_csv(changes_path, index=False)
    print(f"\n=== Pattern changes ===")
    print(f"  Total year-over-year pattern changes detected: {len(changes_df)}")
    print(f"  Companies with at least one change: {changes_df['company_id'].nunique()}")
    print(f"  Saved -> {changes_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()