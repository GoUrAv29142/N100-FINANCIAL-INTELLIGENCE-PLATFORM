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

            "sales_cagr_5yr",
            "pat_cagr_5yr",
            "eps_cagr_5yr",
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


def generate_edge_case_log():
    pass


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