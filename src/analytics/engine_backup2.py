from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
import pandas as pd
from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    debt_to_equity,
    interest_coverage,
    net_debt,
    asset_turnover,
)

from src.analytics.cagr import (
    revenue_cagr,
    pat_cagr,
    eps_cagr,
)

from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern,
)

def load_data():
    """
    Load required tables from the SQLite database.

    Returns
    -------
    dict
        Dictionary containing DataFrames for each required table.
    """

    db_path = Path("db") / "nifty100.db"

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    logging.info("Connecting to SQLite database...")

    conn = sqlite3.connect(db_path)

    try:
        data = {
            "companies": pd.read_sql_query(
                "SELECT * FROM companies",
                conn,
            ),
            "profitandloss": pd.read_sql_query(
                "SELECT * FROM profitandloss",
                conn,
            ),
            "balancesheet": pd.read_sql_query(
                "SELECT * FROM balancesheet",
                conn,
            ),
            "cashflow": pd.read_sql_query(
                "SELECT * FROM cashflow",
                conn,
            ),
        }

        logging.info("Successfully loaded source tables.")

        for table_name, df in data.items():
            logging.info("%s : %d rows", table_name, len(df))

        return data

    finally:
        conn.close()


def calculate_ratios(data):
    """
    Merge financial statement tables into one DataFrame.
    """

    logging.info("Preparing merged financial dataset...")

    pnl = data["profitandloss"].copy()
    bs = data["balancesheet"].copy()
    cf = data["cashflow"].copy()
    companies = data["companies"].copy()
    companies["id"] = companies["id"].astype(str).str.strip()

    # Standardize join keys
    for df in [pnl, bs, cf]:

        df["company_id"] = (
            df["company_id"]
            .astype(str)
            .str.strip()
        )

        df["year"] = (
            pd.to_numeric(df["year"], errors="coerce")
            .astype("Int64")
        )

    # Merge Profit & Loss with Balance Sheet
    merged = pnl.merge(
        bs,
        on=["company_id", "year"],
        how="inner",
        suffixes=("_pnl", "_bs"),
    )

    # Merge Cash Flow
    merged = merged.merge(
        cf,
        on=["company_id", "year"],
        how="inner",
    )
    # Merge companies (face_value needed for book_value_per_share,
    # roce_percentage/roe_percentage needed for Day 13 cross-checks)
    merged = merged.merge(
        companies[["id", "face_value", "roce_percentage", "roe_percentage"]],
        left_on="company_id",
        right_on="id",
        how="left",
    )

    # Merge sectors (broad_sector needed for Financials carve-out, Day 13)
    sectors_df = pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", sqlite3.connect(Path("db") / "nifty100.db"))
    sectors_df["company_id"] = sectors_df["company_id"].astype(str).str.strip()
    merged = merged.merge(sectors_df, on="company_id", how="left")
    merged["is_financials"] = merged["broad_sector"] == "Financials"


    # -----------------------------
    # Profitability Ratios
    # -----------------------------

    merged["net_profit_margin_pct"] = merged.apply(
        lambda row: net_profit_margin(
            row["net_profit"],
            row["sales"],
        ),
        axis=1,
    )

    merged["operating_profit_margin_pct"] = merged.apply(
        lambda row: operating_profit_margin(
            row["operating_profit"],
            row["sales"],
            row["opm_percentage"],
        ),
        axis=1,
    )

    merged["return_on_equity_pct"] = merged.apply(
        lambda row: return_on_equity(
            row["net_profit"],
            row["equity_capital"],
            row["reserves"],
        ),
        axis=1,
    )

    merged["return_on_capital_employed_pct"] = merged.apply(
        lambda row: return_on_capital_employed(
            row["operating_profit"],
            row["other_income"],
            row["equity_capital"],
            row["reserves"],
            row["borrowings"],
        ),
        axis=1,
    )

    merged["return_on_assets_pct"] = merged.apply(
        lambda row: return_on_assets(
            row["net_profit"],
            row["total_assets"],
        ),
        axis=1,
    )

    logging.info("Calculated profitability ratios.")
               # -----------------------------
    # Leverage & Efficiency Ratios
    # -----------------------------

    de_results = merged.apply(
        lambda row: debt_to_equity(
            row["borrowings"],
            row["equity_capital"],
            row["reserves"],
            row["is_financials"],
        ),
        axis=1,
    )

    merged["debt_to_equity"] = de_results.apply(lambda x: x[0])
    merged["high_leverage_flag"] = de_results.apply(lambda x: x[1])


    icr_results = merged.apply(
        lambda row: interest_coverage(
            row["operating_profit"],
            row["other_income"],
            row["interest"],
        ),
        axis=1,
    )

    merged["interest_coverage"] = icr_results.apply(lambda x: x[0])
    merged["icr_label"] = icr_results.apply(lambda x: x[1])
    merged["interest_warning_flag"] = icr_results.apply(lambda x: x[2])


    merged["net_debt"] = merged.apply(
        lambda row: net_debt(
            row["borrowings"],
            row["investments"],
        ),
        axis=1,
    )


    merged["asset_turnover"] = merged.apply(
        lambda row: asset_turnover(
            row["sales"],
            row["total_assets"],
        ),
        axis=1,
    )

    logging.info("Calculated leverage & efficiency ratios.")
    # -----------------------------
    # Direct / pass-through KPIs (Sprint 2 Phase 2)
    # -----------------------------

    def _book_value_per_share(row):
        equity_capital = row["equity_capital"]
        reserves = row["reserves"]
        face_value = row["face_value"]
        if face_value is None or face_value == 0 or pd.isna(face_value):
            return None
        num_shares = equity_capital / face_value
        if num_shares == 0:
            return None
        return round((equity_capital + reserves) / num_shares, 2)

    merged["book_value_per_share"] = merged.apply(_book_value_per_share, axis=1)

    merged["dividend_payout_ratio_pct"] = merged["dividend_payout"]

    merged["total_debt_cr"] = merged["borrowings"]

    merged["cash_from_operations_cr"] = merged["operating_activity"]

    logging.info("Calculated direct pass-through KPIs (book value, dividend payout, total debt, CFO).")
    

    # ----------------------------------------
    # Prepare dataset for CAGR calculations
    # ----------------------------------------

    merged = (
    merged.sort_values(
        ["company_id", "year"]
    )
    .reset_index(drop=True)
)
    logging.info("Prepared dataset for CAGR calculations.")

    # ----------------------------------------
    # CAGR Calculations
    # ----------------------------------------

    # ---------------- Revenue CAGR ----------------
    for period in [3, 5, 10]:
       merged[f"sales_cagr_{period}yr"] = None
       merged[f"sales_cagr_{period}yr_flag"] = None

    # ---------------- PAT CAGR ----------------
    for period in [3, 5, 10]:
       merged[f"pat_cagr_{period}yr"] = None
       merged[f"pat_cagr_{period}yr_flag"] = None

    # ---------------- EPS CAGR ----------------
    for period in [3, 5, 10]:
       merged[f"eps_cagr_{period}yr"] = None
       merged[f"eps_cagr_{period}yr_flag"] = None

    
        # ----------------------------------------
    # Populate CAGR values
    # ----------------------------------------

    for company_id, company_data in merged.groupby("company_id"):

        company_data = company_data.sort_values("year")

        for current_index in company_data.index:

            current_year = merged.loc[current_index, "year"]

            for period in [3, 5, 10]:

                start_year = current_year - period

                previous = company_data[
                    company_data["year"] == start_year
                ]

                if previous.empty:
                    continue

                start = previous.iloc[0]
                end = merged.loc[current_index]

                years_available = current_year - start_year

                # Revenue CAGR
                value, flag = revenue_cagr(
                    start["sales"],
                    end["sales"],
                    years_available,
                    period,
                )

                merged.loc[current_index, f"sales_cagr_{period}yr"] = value
                merged.loc[current_index, f"sales_cagr_{period}yr_flag"] = flag

                # PAT CAGR
                value, flag = pat_cagr(
                    start["net_profit"],
                    end["net_profit"],
                    years_available,
                    period,
                )

                merged.loc[current_index, f"pat_cagr_{period}yr"] = value
                merged.loc[current_index, f"pat_cagr_{period}yr_flag"] = flag

                # EPS CAGR
                value, flag = eps_cagr(
                    start["eps"],
                    end["eps"],
                    years_available,
                    period,
                )

                merged.loc[current_index, f"eps_cagr_{period}yr"] = value
                merged.loc[current_index, f"eps_cagr_{period}yr_flag"] = flag

    logging.info("Calculated CAGR metrics.")


    # ----------------------------------------
    # Cash Flow KPIs
    # ----------------------------------------

    merged["free_cash_flow_cr"] = merged.apply(
    lambda row: free_cash_flow(
        row["operating_activity"],
        row["investing_activity"],
    ),
    axis=1,
)


    merged["fcf_conversion_rate"] = merged.apply(
    lambda row: fcf_conversion_rate(
        row["free_cash_flow_cr"],
        row["operating_profit"],
    ),
    axis=1,
)


    capex_results = merged.apply(
    lambda row: capex_intensity(
        row["investing_activity"],
        row["sales"],
    ),
    axis=1,
)


    merged["capex_intensity_pct"] = capex_results.apply(
    lambda x: x[0]
)


    merged["capex_classification"] = capex_results.apply(
    lambda x: x[1]
)


    # ----------------------------------------
    # Capital Allocation Classification
    #-----------------------------------------

    merged["capital_allocation_pattern"] = merged.apply(
    lambda row: capital_allocation_pattern(
        row["operating_activity"],
        row["investing_activity"],
        row["financing_activity"],
    ),
    axis=1,
)


    logging.info("Calculated cash flow KPIs.")

    # ----------------------------------------
    # CFO Quality Score (5-year average)
    # ----------------------------------------

    merged["cfo_pat_ratio"] = None
    merged["cfo_quality_score"] = None


    for company_id, company_data in merged.groupby("company_id"):

        company_data = company_data.sort_values("year")


        for idx in company_data.index:

            current_year = merged.loc[idx, "year"]

            last_5_years = company_data[
                (company_data["year"] <= current_year)
                &
                (company_data["year"] > current_year - 5)
            ]


            ratios = []

            for _, row in last_5_years.iterrows():

                if row["net_profit"] == 0:
                    continue

                ratios.append(
                    row["operating_activity"]
                    /
                    row["net_profit"]
                )


            if ratios:

                avg_ratio = round(
                    sum(ratios) / len(ratios),
                    2
                )

                merged.loc[idx, "cfo_pat_ratio"] = avg_ratio


                merged.loc[idx, "cfo_quality_score"] = (
                    cfo_quality_score(avg_ratio)
                )
    # ----------------------------------------
    # Composite Quality Score
    # ----------------------------------------
    # 0.3*ROE_score + 0.25*FCF_score + 0.25*ROCE_score + 0.20*DE_score
    # Each component winsorized at P10/P90 then scaled 0-100.
    # D/E is inverted (lower D/E = higher score, since less debt is better).

    def _winsorize_and_score(series, invert=False):
        s = series.copy().astype(float)
        valid = s.dropna()
        if len(valid) < 2:
            return pd.Series([None] * len(s), index=s.index)

        p10 = valid.quantile(0.10)
        p90 = valid.quantile(0.90)

        clipped = s.clip(lower=p10, upper=p90)

        if p90 == p10:
            return pd.Series([50.0 if pd.notna(v) else None for v in s], index=s.index)

        score = (clipped - p10) / (p90 - p10) * 100
        if invert:
            score = 100 - score

        return score.where(s.notna(), None)

    roe_score = _winsorize_and_score(merged["return_on_equity_pct"])
    fcf_score = _winsorize_and_score(merged["free_cash_flow_cr"])
    roce_score = _winsorize_and_score(merged["return_on_capital_employed_pct"])
    de_score = _winsorize_and_score(merged["debt_to_equity"], invert=True)

    def _combine(row_idx):
        scores = [
            (roe_score.get(row_idx), 0.30),
            (fcf_score.get(row_idx), 0.25),
            (roce_score.get(row_idx), 0.25),
            (de_score.get(row_idx), 0.20),
        ]
        valid_scores = [(s, w) for s, w in scores if s is not None and pd.notna(s)]
        if not valid_scores:
            return None
        total_weight = sum(w for _, w in valid_scores)
        weighted_sum = sum(s * w for s, w in valid_scores)
        return round(weighted_sum / total_weight, 2)

    merged["composite_quality_score"] = [
        _combine(idx) for idx in merged.index
    ]

    logging.info("Calculated composite quality scores.")

   


    return merged

def populate_financial_ratios(df):

    db_path = Path("db") / "nifty100.db"

    conn = sqlite3.connect(db_path)

    # Clear old records
    conn.execute("DELETE FROM financial_ratios")
    conn.commit()

    output = df[
        [
            "company_id",
            "year",

            "net_profit_margin_pct",
            "operating_profit_margin_pct",
            "return_on_equity_pct",
            "return_on_capital_employed_pct",
            "return_on_assets_pct",

            "debt_to_equity",
            "interest_coverage",
            "asset_turnover",

            "free_cash_flow_cr",
            "capex_intensity_pct",

            "eps",
            "book_value_per_share",
            "dividend_payout_ratio_pct",
            "total_debt_cr",
            "cash_from_operations_cr",

            "sales_cagr_5yr",
            "pat_cagr_5yr",
            "eps_cagr_5yr",
            "composite_quality_score",
        ]
    ].copy()

    output.rename(
        columns={
            
            "capex_intensity_pct": "capex_cr",
            "eps": "earnings_per_share",
            "sales_cagr_5yr": "revenue_cagr_5yr",
        },
        inplace=True
    )

    output.to_sql(
        "financial_ratios",
        conn,
        if_exists="append",
        index=False
    )

    conn.close()

    logging.info(
        "financial_ratios table populated: %d rows",
        len(output)
    )

def generate_capital_allocation(merged):

    output = merged.copy()

    output["cfo_sign"] = output["operating_activity"].apply(
        lambda x: "+" if x >= 0 else "-"
    )

    output["cfi_sign"] = output["investing_activity"].apply(
        lambda x: "+" if x >= 0 else "-"
    )

    output["cff_sign"] = output["financing_activity"].apply(
        lambda x: "+" if x >= 0 else "-"
    )

    output = output[
        [
            "company_id",
            "year",
            "cfo_sign",
            "cfi_sign",
            "cff_sign",
            "capital_allocation_pattern",
        ]
    ]

    output = output.rename(
        columns={
            "capital_allocation_pattern": "pattern_label"
        }
    )

    Path("output").mkdir(
        exist_ok=True
    )

    output.to_csv(
        "output/capital_allocation.csv",
        index=False,
    )

    logging.info(
        "Generated output/capital_allocation.csv"
    )


def generate_edge_case_log(merged):
    """
    Day 13 deliverable: output/ratio_edge_cases.log

    Cross-checks computed ROCE and ROE against the pre-computed
    roce_percentage / roe_percentage fields in companies.xlsx, and logs
    every CAGR turnaround / debt-free substitution already flagged
    elsewhere in `merged`. Every anomaly is categorised as one of:
    DATA_SOURCE_ISSUE, VERSION_DIFFERENCE, or FORMULA_DISCREPANCY.
    """
    Path("output").mkdir(exist_ok=True)
    log_path = Path("output") / "ratio_edge_cases.log"

    lines = []
    lines.append(f"Ratio Edge Case Log - generated {pd.Timestamp.now().isoformat(timespec='seconds')}")
    lines.append("=" * 80)

    # Only cross-check the LATEST year per company, since roce_percentage
    # and roe_percentage in companies.xlsx are current snapshot values,
    # not historical - comparing every year against a single snapshot
    # produces false positives for all older years.
    latest_year_idx = merged.groupby("company_id")["year"].idxmax()
    latest_rows = merged.loc[latest_year_idx]

    # --- 1. ROCE Cross-Check (latest year only, diff > 5%) ---
    lines.append("\n--- ROCE Cross-Check: latest year vs companies.roce_percentage (diff > 5%) ---")
    roce_anomaly_count = 0
    for _, row in latest_rows.iterrows():
        computed = row.get("return_on_capital_employed_pct")
        reported = row.get("roce_percentage")
        if computed is None or reported is None or pd.isna(computed) or pd.isna(reported):
            continue
        diff = abs(computed - reported)
        if diff > 5:
            roce_anomaly_count += 1
            category = "VERSION_DIFFERENCE" if row.get("is_financials") else "FORMULA_DISCREPANCY"
            lines.append(
                f"{row['company_id']} {row['year']} (latest): computed_ROCE={computed:.2f}% "
                f"reported_ROCE={reported:.2f}% diff={diff:.2f}% "
                f"sector={'Financials (sector-relative benchmark applies)' if row.get('is_financials') else 'Non-Financials'} "
                f"category={category}"
            )
    lines.append(f"Total ROCE anomalies logged: {roce_anomaly_count}")
# --- 2. ROE Cross-Check (latest year only, diff > 5%, or unit-mismatch) ---
    lines.append("\n--- ROE Cross-Check: latest year vs companies.roe_percentage (diff > 5%) ---")
    roe_anomaly_count = 0
    for _, row in latest_rows.iterrows():
        computed = row.get("return_on_equity_pct")
        reported = row.get("roe_percentage")
        if computed is None or reported is None or pd.isna(computed) or pd.isna(reported):
            continue
        if reported < 1.0 and computed > 5.0:
            roe_anomaly_count += 1
            lines.append(
                f"{row['company_id']} {row['year']} (latest): computed_ROE={computed:.2f}% "
                f"reported_ROE={reported} looks unit-mismatched (fraction vs percent) "
                f"category=DATA_SOURCE_ISSUE"
            )
            continue
        diff = abs(computed - reported)
        if diff > 5:
            roe_anomaly_count += 1
            lines.append(
                f"{row['company_id']} {row['year']} (latest): computed_ROE={computed:.2f}% "
                f"reported_ROE={reported:.2f}% diff={diff:.2f}% "
                f"category=FORMULA_DISCREPANCY"
            )
    lines.append(f"Total ROE anomalies logged: {roe_anomaly_count}")

    

    # --- 2b. Extreme ROE outliers (any year, |computed ROE| > 500%) ---
    # These indicate a near-zero equity+reserves denominator, not a
    # snapshot-timing mismatch. Flagged separately for investigation.
    lines.append("\n--- Extreme ROE Outliers (|computed ROE| > 500%, denominator likely near-zero) ---")
    extreme = merged[merged["return_on_equity_pct"].abs() > 500]
    lines.append(f"Total extreme ROE outlier rows: {len(extreme)}")
    for _, row in extreme.iterrows():
        total_equity = row["equity_capital"] + row["reserves"]
        lines.append(
            f"{row['company_id']} {row['year']}: computed_ROE={row['return_on_equity_pct']:.2f}% "
            f"equity_capital={row['equity_capital']} reserves={row['reserves']} "
            f"total_equity={total_equity:.2f} category=FORMULA_EDGE_CASE_NEAR_ZERO_DENOMINATOR"
        )

   
    # --- 3. Debt-free substitutions (ICR = None, displayed as 'Debt Free') ---
    lines.append("\n--- Debt-Free ICR Substitutions ---")
    debt_free_rows = merged[merged["icr_label"] == "Debt Free"]
    lines.append(f"Total debt-free company-years (ICR substituted): {len(debt_free_rows)}")

    # --- 4. CAGR turnaround / edge flags already computed ---
    lines.append("\n--- CAGR Edge Case Flags (non-null flags across 3/5/10yr, revenue/PAT/EPS) ---")
    flag_cols = [c for c in merged.columns if c.endswith("_flag") and "cagr" in c]
    total_flagged = 0
    for col in flag_cols:
        count = merged[col].notna().sum()
        if count > 0:
            lines.append(f"{col}: {count} flagged rows")
            total_flagged += count
    lines.append(f"Total CAGR edge-case flags across all periods/metrics: {total_flagged}")

    # --- 5. High leverage flags (non-financials only, D/E > 5) ---
    lines.append("\n--- High Leverage Flags (D/E > 5, non-Financials only) ---")
    high_lev_count = merged["high_leverage_flag"].sum() if "high_leverage_flag" in merged.columns else 0
    lines.append(f"Total high-leverage flags: {int(high_lev_count)}")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logging.info("Generated %s", log_path)


def main():

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    tables = load_data()

    merged = calculate_ratios(tables)
    print("\nColumns in merged dataframe:")
    print(sorted(merged.columns.tolist()))
    populate_financial_ratios(merged)
    generate_capital_allocation(merged)
    generate_edge_case_log(merged)

    print("\nMerged Dataset\n")
    print(merged.shape)
    print()
    print(
    merged[
        [
            "company_id",
            "year",

            "sales_cagr_3yr",
            "sales_cagr_5yr",
            "sales_cagr_10yr",

            "pat_cagr_3yr",
            "pat_cagr_5yr",
            "pat_cagr_10yr",

            "eps_cagr_3yr",
            "eps_cagr_5yr",
            "eps_cagr_10yr",
        ]
    ].head(20)
)

if __name__ == "__main__":
    main()