"""
src/etl/loader.py

Reads the 12 raw Excel files in data/raw/core/ into clean pandas
DataFrames, applying the correct header row per file and normalising
company_id / year columns via normaliser.py.

Two header layouts were found by inspecting the real files (Day 02):
  BANNER_HEADER_FILES : row 0 is a title banner, real headers on row 1
                         (i.e. header=1 in pandas' 0-indexed terms)
  CLEAN_HEADER_FILES   : headers already on row 0 (header=0, the default)

Rejected rows during normalization / FK filtering are now logged to
output/validation_failures.csv (DQ-07, DQ-08, DQ-03) instead of being
silently dropped, per Sprint 2 row-count investigation findings.
"""

import csv
from pathlib import Path
from typing import Dict

import pandas as pd

from nifty100_dashboard.src.etl.normaliser import (
    normalize_ticker,
    normalize_year,
    YearNormalizationError,
    TickerNormalizationError,
)
from nifty100_dashboard.src.config import RAW_DATA_DIR  # Path to data/raw/core, from Day 01 config.py
from nifty100_dashboard.src.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------
# File -> (sheet_name, header_row) map, from real inspection
# ---------------------------------------------------------------------
FILES = {
    "companies":       {"file": "companies.xlsx",       "sheet": "Companies",     "header": 1},
    "profitandloss":   {"file": "profitandloss.xlsx",   "sheet": "Profit & Loss", "header": 1},
    "balancesheet":    {"file": "balancesheet.xlsx",    "sheet": "Balance Sheet", "header": 1},
    "cashflow":        {"file": "cashflow.xlsx",        "sheet": "Cash Flow",     "header": 1},
    "analysis":        {"file": "analysis.xlsx",        "sheet": "Analysis",      "header": 1},
    "documents":       {"file": "documents.xlsx",       "sheet": "Documents",     "header": 1},
    "prosandcons":     {"file": "prosandcons.xlsx",     "sheet": "Pros & Cons",   "header": 1},
    "sectors":         {"file": "sectors.xlsx",         "sheet": "Sheet1",        "header": 0},
    "stock_prices":    {"file": "stock_prices.xlsx",    "sheet": "Sheet1",        "header": 0},
    "financial_ratios":{"file": "financial_ratios.xlsx","sheet": "Sheet1",        "header": 0},
    "market_cap":      {"file": "market_cap.xlsx",      "sheet": "Sheet1",        "header": 0},
    "peer_groups":     {"file": "peer_groups.xlsx",     "sheet": "Sheet1",        "header": 0},
}

# Real source files sometimes use different casing/names than schema.sql.
# Found during Day 05 end-to-end testing: documents.xlsx uses 'Year' and
# 'Annual_Report' instead of 'year' / 'annual_report_url'.
COLUMN_RENAMES = {
    "documents": {"Year": "year", "Annual_Report": "annual_report_url"},
}

# Tables that have a `year` column needing normalize_year()
YEAR_TABLES = {
    "profitandloss", "balancesheet", "cashflow",
    "financial_ratios", "market_cap", "documents",
}

# Tables that have a `company_id` column needing normalize_ticker()
# (companies uses `id` instead, handled separately)
COMPANY_ID_TABLES = {
    "profitandloss", "balancesheet", "cashflow", "analysis",
    "documents", "prosandcons", "sectors", "stock_prices",
    "financial_ratios", "market_cap", "peer_groups",
}

# Path to output/validation_failures.csv (project root / output /)
VALIDATION_CSV_PATH = Path(__file__).resolve().parents[2] / "output" / "validation_failures.csv"


def read_raw_sheet(table_name: str) -> pd.DataFrame:
    """Read one raw Excel file into a DataFrame using its correct header row."""
    spec = FILES[table_name]
    path = Path(RAW_DATA_DIR) / spec["file"]
    if not path.exists():
        raise FileNotFoundError(f"Expected source file not found: {path}")

    df = pd.read_excel(path, sheet_name=spec["sheet"], header=spec["header"])

    rename_map = COLUMN_RENAMES.get(table_name)
    if rename_map:
        df = df.rename(columns=rename_map)

    log.info("Read %s: %d rows, %d cols", table_name, len(df), len(df.columns))
    return df


def clean_companies(df: pd.DataFrame) -> pd.DataFrame:
    """companies.xlsx uses `id` (ticker) as primary key, not company_id."""
    df = df.copy()
    df["id"], rejects = _apply_normalizer(df["id"], normalize_ticker)
    if rejects:
        log.warning("companies: %d rows rejected during ticker normalization", len(rejects))
        _log_rejects_to_validation_csv("companies", "DQ-08", rejects, "ticker normalization failed")
    df = df.dropna(subset=["id"])
    return df


def clean_table(table_name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Apply normalize_ticker / normalize_year to the relevant columns."""
    df = df.copy()

    if table_name in COMPANY_ID_TABLES and "company_id" in df.columns:
        df["company_id"], rejects = _apply_normalizer(df["company_id"], normalize_ticker)
        if rejects:
            log.warning("%s: %d rows rejected during ticker normalization", table_name, len(rejects))
            _log_rejects_to_validation_csv(table_name, "DQ-08", rejects, "ticker normalization failed")

    if table_name in YEAR_TABLES and "year" in df.columns:
        df["year"], rejects = _apply_normalizer(df["year"], normalize_year)
        if rejects:
            log.warning("%s: %d rows rejected during year normalization", table_name, len(rejects))
            _log_rejects_to_validation_csv(table_name, "DQ-07", rejects, "year normalization failed")

    # Drop rows where normalization produced a null (i.e. rejected rows)
    subset_cols = [c for c in ("company_id", "year") if c in df.columns]
    if subset_cols:
        df = df.dropna(subset=subset_cols)

    return df


def _apply_normalizer(series: pd.Series, fn):
    """
    Apply a normalizer function element-wise, catching per-row errors
    instead of failing the whole column. Returns (cleaned_series, rejects)
    where rejects is a list of (index, original_value, error) for the
    load_audit.csv / validation_failures.csv report.
    """
    cleaned = []
    rejects = []
    for idx, val in series.items():
        try:
            cleaned.append(fn(val))
        except (YearNormalizationError, TickerNormalizationError) as e:
            cleaned.append(None)
            rejects.append((idx, val, str(e)))
    return pd.Series(cleaned, index=series.index), rejects


def _log_rejects_to_validation_csv(table_name: str, rule: str, rejects: list, detail_prefix: str):
    """
    Append rejected-row records to output/validation_failures.csv using
    the same schema the validator already writes: rule, severity, table,
    row_id, detail. DQ-07, DQ-08, and DQ-03 are all CRITICAL per spec
    Section 14, so previously-silent row drops are now fully documented.
    """
    if not rejects:
        return

    VALIDATION_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = VALIDATION_CSV_PATH.exists()

    with open(VALIDATION_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["rule", "severity", "table", "row_id", "detail"])
        for idx, val, err in rejects:
            writer.writerow([rule, "CRITICAL", table_name, idx, f"{detail_prefix}: {val!r} ({err})"])

    log.info("Logged %d %s rejects for %s to validation_failures.csv", len(rejects), rule, table_name)


def _deduplicate(table_name: str, df: pd.DataFrame, key_cols: list) -> pd.DataFrame:
    """
    Drop duplicate rows on key_cols, keeping the first occurrence.
    Logs how many rows were dropped (feeds load_audit.csv on Day 05).
    """
    before = len(df)
    df = df.drop_duplicates(subset=key_cols, keep="first")
    dropped = before - len(df)
    if dropped:
        log.warning("%s: dropped %d duplicate rows on %s (kept first occurrence)",
                    table_name, dropped, key_cols)
    return df


def _filter_to_known_companies(table_name: str, df: pd.DataFrame, valid_ids: set) -> pd.DataFrame:
    """
    Drop rows whose company_id is not present in companies.id.
    Enforces FK integrity (DQ-03) before write time, so companies stays
    the single source of truth for which 92 tickers are in-scope.
    Rejected rows are now logged to validation_failures.csv.
    """
    if "company_id" not in df.columns:
        return df
    before = len(df)
    orphan_mask = ~df["company_id"].isin(valid_ids)
    orphans = df[orphan_mask]
    df = df[~orphan_mask]
    dropped = before - len(df)
    if dropped:
        log.warning("%s: dropped %d rows with company_id not in companies (%d remain)",
                    table_name, dropped, len(df))
        rejects = [(idx, row["company_id"], "company_id not found in companies.id")
                   for idx, row in orphans.iterrows()]
        _log_rejects_to_validation_csv(table_name, "DQ-03", rejects, "FK integrity failed")
    return df


def load_all_raw() -> Dict[str, pd.DataFrame]:
    """
    Read and clean all 12 source files.

    Load order matters for FK integrity: companies MUST be loaded and
    written to the DB first, since every other table's company_id
    foreign-keys into companies.id.

    Post-processing applied here (decided during Day 03 DQ review):
      - Duplicate (company_id, year) rows in year-keyed tables are
        de-duplicated, keeping the first occurrence.
      - Rows whose company_id is not present in companies.id are
        dropped, so companies.xlsx's 92 tickers remain the single
        source of truth (exit criteria: SELECT COUNT(*) FROM companies = 92).
        These rejections are logged to validation_failures.csv (DQ-03).
      - Rows whose year fails normalization (e.g. 'TTM' trailing-twelve-
        months labels) are dropped and logged (DQ-07), since fiscal-year
        based KPIs (CAGR etc.) cannot use a non-fiscal-year label.
      - market_cap is merged into financial_ratios on (company_id, year),
        matching schema.sql's single financial_ratios table.
    """
    tables: Dict[str, pd.DataFrame] = {}

    # 1. companies first (anchor table)
    raw_companies = read_raw_sheet("companies")
    tables["companies"] = clean_companies(raw_companies)
    valid_ids = set(tables["companies"]["id"])

    # 2. everything else
    for name in FILES:
        if name == "companies":
            continue
        raw = read_raw_sheet(name)
        df = clean_table(name, raw)
        df = _filter_to_known_companies(name, df, valid_ids)
        if name in {"profitandloss", "balancesheet", "cashflow", "financial_ratios", "market_cap"}:
            df = _deduplicate(name, df, key_cols=["company_id", "year"])
        tables[name] = df

    # 3. merge market_cap into financial_ratios (schema.sql has one combined table)
    if "market_cap" in tables and "financial_ratios" in tables:
        fr = tables["financial_ratios"]
        mc = tables["market_cap"].drop(columns=["id"], errors="ignore")
        merged = fr.merge(mc, on=["company_id", "year"], how="left", suffixes=("", "_mc"))
        tables["financial_ratios"] = merged
        del tables["market_cap"]
        log.info("Merged market_cap into financial_ratios: %d rows", len(merged))

    return tables


if __name__ == "__main__":
    tables = load_all_raw()
    for name, df in tables.items():
        print(f"{name}: {len(df)} rows")