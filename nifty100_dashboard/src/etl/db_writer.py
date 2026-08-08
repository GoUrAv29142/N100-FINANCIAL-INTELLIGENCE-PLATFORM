"""
src/etl/db_writer.py

Day 05: writes the cleaned, validated tables (from loader.load_all_raw())
into nifty100.db, in FK-safe order, and produces output/load_audit.csv
with per-table row counts AND rejection counts, plus output/validation_failures.csv
covering both loader-stage rejects (DQ-03/07/08) and validator-stage findings
(DQ-04/05/06/etc.) in one combined file.

Usage:
    python -m src.etl.db_writer
"""

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

from nifty100_dashboard.src.etl.loader import load_all_raw, FILES
from nifty100_dashboard.src.etl.validator import run_all_rules, has_critical_failures
from nifty100_dashboard.src.logger import get_logger

log = get_logger(__name__)

DB_PATH = Path("db") / "nifty100.db"
SCHEMA_PATH = Path("db") / "schema.sql"
AUDIT_PATH = Path("output") / "load_audit.csv"
FAILURES_PATH = Path("output") / "validation_failures.csv"

# Write order matters: companies first (FK anchor), then everything else.
TABLE_WRITE_ORDER = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "financial_ratios",
    "peer_groups",
]

# Approximate raw row counts per source file, used only to compute
# "rejected" for load_audit.csv (rows_in - rows_out). Read fresh from
# disk rather than hardcoded so this stays accurate if source files change.
def _get_raw_row_counts() -> Dict[str, int]:
    from nifty100_dashboard.src.etl.loader import read_raw_sheet
    counts = {}
    for name in FILES:
        try:
            counts[name] = len(read_raw_sheet(name))
        except Exception as e:
            log.warning("Could not read raw count for %s: %s", name, e)
            counts[name] = None
    return counts


def rebuild_schema(conn: sqlite3.Connection) -> None:
    """Drop and recreate all tables from schema.sql, so re-runs start clean."""
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    log.info("Schema applied from %s", SCHEMA_PATH)


def write_tables(conn: sqlite3.Connection, tables: Dict[str, pd.DataFrame],
                  raw_counts: Dict[str, int]) -> pd.DataFrame:
    """
    Write each table to SQLite via pandas.to_sql, in FK-safe order.
    Returns an audit DataFrame: table, rows_in, rows_out, rejected, timestamp, runtime_s.
    """
    audit_rows = []

    for name in TABLE_WRITE_ORDER:
        df = tables.get(name)
        if df is None:
            log.warning("No DataFrame found for table %s - skipping", name)
            continue

        start = time.time()
        df.to_sql(name, conn, if_exists="append", index=False)
        runtime_s = round(time.time() - start, 3)

        rows_out = len(df)
        rows_in = raw_counts.get(name)
        rejected = (rows_in - rows_out) if rows_in is not None else None

        audit_rows.append({
            "table": name,
            "rows_in": rows_in,
            "rows_out": rows_out,
            "rejected": rejected,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "runtime_s": runtime_s,
        })
        log.info("Wrote %s: %d rows (rejected: %s)", name, rows_out, rejected)

    conn.commit()
    return pd.DataFrame(audit_rows)


def verify_load(conn: sqlite3.Connection) -> None:
    """Run the Day 05 exit-criteria checks and print results."""
    n_companies = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    print(f"\nSELECT COUNT(*) FROM companies = {n_companies} "
          f"({'PASS' if n_companies == 92 else 'FAIL - expected 92'})")

    fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    print(f"PRAGMA foreign_key_check -> {len(fk_violations)} rows "
          f"({'PASS' if len(fk_violations) == 0 else 'FAIL'})")
    if fk_violations:
        for v in fk_violations[:10]:
            print("  ", v)


def main():
    Path("output").mkdir(exist_ok=True)

    # 0. Start validation_failures.csv fresh for this run. loader.py will
    #    APPEND DQ-03/DQ-07/DQ-08 rejects into this file during load_all_raw().
    if FAILURES_PATH.exists():
        FAILURES_PATH.unlink()
        log.info("Cleared %s for a fresh run", FAILURES_PATH)

    # 1. Capture raw row counts BEFORE cleaning, for load_audit.csv rejected column
    raw_counts = _get_raw_row_counts()

    # 2. Load and clean all 12 source files (Day 02 loader, with Day 03 fixes).
    #    This APPENDS DQ-03/07/08 rejects to validation_failures.csv internally.
    tables = load_all_raw()

    # 3. Run validator on the cleaned tables for remaining WARNING-level rules
    #    (DQ-04, DQ-05, DQ-06, DQ-09 through DQ-16). APPEND, do not overwrite,
    #    so loader-stage CRITICAL rejects from step 2 are preserved.
    failures_df = run_all_rules(tables)
    write_header = not FAILURES_PATH.exists()
    failures_df.to_csv(FAILURES_PATH, mode="a", header=write_header, index=False)
    print(f"Validation: {len(failures_df)} additional validator-stage failures "
          f"appended to {FAILURES_PATH}")

    # 4. Re-read the COMBINED file (loader-stage + validator-stage) to check
    #    for critical failures before writing to the database.
    combined_failures = pd.read_csv(FAILURES_PATH)
    print(f"Total combined validation_failures.csv rows: {len(combined_failures)}")
    print(combined_failures["severity"].value_counts().to_string())

    # NOTE: DQ-03/07/08 CRITICAL rejects represent rows already EXCLUDED
    # from `tables` by loader.py (this is correct, documented behavior -
    # see loader.py docstring). They should NOT abort the load, since the
    # rejection already happened safely. Only abort if the validator finds
    # CRITICAL issues remaining IN the cleaned data itself (e.g. duplicate
    # PKs that survived cleaning) - i.e. failures produced by run_all_rules
    # in step 3, not the loader-stage exclusions from step 2.
    if has_critical_failures(failures_df):
        print("\n*** CRITICAL failures found in CLEANED data. Aborting load. ***")
        print("Resolve CRITICAL rows in validation_failures.csv before re-running.")
        return

    # 5. Fresh DB: remove existing file, rebuild schema, write tables
    if DB_PATH.exists():
        DB_PATH.unlink()
        log.info("Removed existing %s for a clean load", DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    rebuild_schema(conn)
    audit_df = write_tables(conn, tables, raw_counts)
    audit_df.to_csv(AUDIT_PATH, index=False)
    print(f"\nLoad audit written to {AUDIT_PATH}")
    print(audit_df.to_string(index=False))

    verify_load(conn)

    conn.close()


if __name__ == "__main__":
    main()