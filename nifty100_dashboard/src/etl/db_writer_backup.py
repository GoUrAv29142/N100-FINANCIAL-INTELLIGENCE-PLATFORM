"""
src/etl/db_writer.py

Day 05: writes the cleaned, validated tables (from loader.load_all_raw())
into nifty100.db, in FK-safe order, and produces output/load_audit.csv
with per-table row counts.

Usage:
    python -m src.etl.db_writer
"""

import sqlite3
from pathlib import Path
from typing import Dict

import pandas as pd

from nifty100_dashboard.src.etl.loader import load_all_raw
from nifty100_dashboard.src.etl.validator import run_all_rules, has_critical_failures
from nifty100_dashboard.src.logger import get_logger

log = get_logger(__name__)

DB_PATH = Path("db") / "nifty100.db"
SCHEMA_PATH = Path("db") / "schema.sql"
AUDIT_PATH = Path("output") / "load_audit.csv"
FAILURES_PATH = Path("output") / "validation_failures.csv"

# Write order matters: companies first (FK anchor), then everything else.
# Order among the rest doesn't matter for FK purposes since they all only
# reference companies, not each other.
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


def rebuild_schema(conn: sqlite3.Connection) -> None:
    """Drop and recreate all tables from schema.sql, so re-runs start clean."""
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    log.info("Schema applied from %s", SCHEMA_PATH)


def write_tables(conn: sqlite3.Connection, tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Write each table to SQLite via pandas.to_sql, in FK-safe order.
    Returns an audit DataFrame: table, rows_loaded.
    """
    audit_rows = []

    for name in TABLE_WRITE_ORDER:
        df = tables.get(name)
        if df is None:
            log.warning("No DataFrame found for table %s — skipping", name)
            continue

        df.to_sql(name, conn, if_exists="append", index=False)
        n = len(df)
        audit_rows.append({"table": name, "rows_loaded": n})
        log.info("Wrote %s: %d rows", name, n)

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

    # 1. Load and clean all 12 source files (Day 02 loader, with Day 03 fixes)
    tables = load_all_raw()

    # 2. Re-run validator on the cleaned tables; write validation_failures.csv
    failures_df = run_all_rules(tables)
    failures_df.to_csv(FAILURES_PATH, index=False)
    print(f"Validation: {len(failures_df)} failures written to {FAILURES_PATH}")

    if has_critical_failures(failures_df):
        print("\n*** CRITICAL failures present. Aborting load. ***")
        print("Resolve CRITICAL rows in validation_failures.csv before re-running.")
        return

    # 3. Fresh DB: remove existing file, rebuild schema, write tables
    if DB_PATH.exists():
        DB_PATH.unlink()
        log.info("Removed existing %s for a clean load", DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    rebuild_schema(conn)
    audit_df = write_tables(conn, tables)
    audit_df.to_csv(AUDIT_PATH, index=False)
    print(f"\nLoad audit written to {AUDIT_PATH}")
    print(audit_df.to_string(index=False))

    verify_load(conn)

    conn.close()


if __name__ == "__main__":
    main()