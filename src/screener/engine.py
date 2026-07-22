"""
src/screener/engine.py

Day 15: Filter Engine Core for the Investment Screener (Module 3).
Loads thresholds from config/screener_config.yaml and applies them to
the financial_ratios table, with special handling for:
  - D/E filters: automatically skipped for Financials-sector companies
    (high leverage is structurally normal for banks/NBFCs/insurance).
  - ICR filters: "Debt Free" (interest = 0, icr_label = "Debt Free")
    always passes any ICR minimum threshold, treated as infinity.
"""

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

DB_PATH = Path("db") / "nifty100.db"
CONFIG_PATH = Path("config") / "screener_config.yaml"


def load_config() -> dict:
    """Load filter/preset definitions from screener_config.yaml."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def load_universe(year: Optional[int] = None) -> pd.DataFrame:
    """
    Load the financial_ratios universe, joined with sectors (for the
    Financials carve-out) and companies (for company_name display).

    If year is None, uses each company's latest available year.
    """
    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        """
        SELECT fr.*, s.broad_sector, c.company_name
        FROM financial_ratios fr
        LEFT JOIN sectors s ON fr.company_id = s.company_id
        LEFT JOIN companies c ON fr.company_id = c.id
        """,
        conn,
    )
    conn.close()

    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    if year is not None:
        df = df[df["year"] == year]
    else:
        latest_idx = df.groupby("company_id")["year"].idxmax()
        df = df.loc[latest_idx]

    df["is_financials"] = df["broad_sector"] == "Financials"

    return df.reset_index(drop=True)


def _passes_filter(df: pd.DataFrame, filter_name: str, threshold: float, filter_defs: dict) -> pd.Series:
    """
    Apply a single named filter to the universe, returning a boolean mask.
    Handles the D/E Financials-skip and ICR Debt-Free-always-passes rules.
    """
    fdef = filter_defs[filter_name]
    column = fdef["column"]
    direction = fdef["direction"]

    if column not in df.columns:
        raise KeyError(f"Filter '{filter_name}' references unknown column '{column}'")

    values = df[column]

    if direction == "min":
        mask = values >= threshold
    elif direction == "max":
        mask = values <= threshold
    else:
        raise ValueError(f"Unknown filter direction: {direction}")

    # D/E: skip the check entirely for Financials-sector companies -
    # they always pass this specific filter regardless of their D/E value.
    if fdef.get("skip_for_financials"):
        mask = mask | df["is_financials"]

    # ICR: "Debt Free" companies (icr_label == "Debt Free") always pass
    # any ICR minimum threshold, treated as ICR = infinity.
    if fdef.get("debt_free_always_passes") and "icr_label" in df.columns:
        mask = mask | (df["icr_label"] == "Debt Free")

    # Missing/null values never pass a threshold filter (can't evaluate)
    mask = mask & values.notna() | (
        mask & fdef.get("skip_for_financials", False) & df["is_financials"]
    )

    return mask.fillna(False)


def run_filters(df: pd.DataFrame, thresholds: dict, filter_defs: dict) -> pd.DataFrame:
    """
    Apply a dict of {filter_name: threshold_value} to the universe.
    Returns the filtered, sorted DataFrame with composite_quality_score.
    """
    combined_mask = pd.Series(True, index=df.index)

    for filter_name, threshold in thresholds.items():
        if filter_name not in filter_defs:
            continue  # e.g. dividend_payout_max, revenue_cagr_3yr_min not yet in filter_defs
        mask = _passes_filter(df, filter_name, threshold, filter_defs)
        combined_mask = combined_mask & mask

    result = df[combined_mask].copy()
    result = result.sort_values("composite_quality_score", ascending=False, na_position="last")

    return result.reset_index(drop=True)


if __name__ == "__main__":
    config = load_config()
    universe = load_universe()

    print(f"Universe size (latest year per company): {len(universe)}")

    # Quick manual test: ROE > 15, D/E < 1
    test_thresholds = {"roe_min": 15, "de_max": 1.0}
    result = run_filters(universe, test_thresholds, config["filters"])
    print(f"\nROE>15 AND D/E<1 test filter: {len(result)} companies")
    print(result[["company_id", "return_on_equity_pct", "debt_to_equity", "is_financials", "composite_quality_score"]].head(10).to_string())