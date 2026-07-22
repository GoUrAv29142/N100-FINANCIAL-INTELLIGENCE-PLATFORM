-- =====================================================================
-- nifty100.db — SQLite Schema
-- Sprint 1 · Day 04 · Data Ingestion & ETL
--
-- IMPORTANT: company_id everywhere is the TICKER SYMBOL (e.g. "ABB",
-- "HDFCBANK"), not a numeric surrogate key. companies.id is TEXT and
-- is the anchor every other table's company_id foreign-keys into.
--
-- 12 source files -> 11 tables (market_cap.xlsx merged into
-- financial_ratios, since both are keyed by company_id + year).
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1. companies  (anchor table — from companies.xlsx)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    id                  TEXT PRIMARY KEY,      -- ticker, e.g. 'ABB'
    company_logo        TEXT,
    company_name        TEXT NOT NULL,
    chart_link          TEXT,
    about_company       TEXT,
    website             TEXT,
    nse_profile         TEXT,
    bse_profile         TEXT,
    face_value          REAL,
    book_value          REAL,
    roce_percentage     REAL,
    roe_percentage      REAL
);

-- ---------------------------------------------------------------------
-- 2. profitandloss  (from profitandloss.xlsx)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profitandloss (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL,
    year                TEXT NOT NULL,          -- normalized, e.g. '2012-12'
    sales               REAL,
    expenses            REAL,
    operating_profit    REAL,
    opm_percentage      REAL,
    other_income        REAL,
    interest            REAL,
    depreciation        REAL,
    profit_before_tax   REAL,
    tax_percentage      REAL,
    net_profit          REAL,
    eps                 REAL,
    dividend_payout     REAL,
    UNIQUE (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ---------------------------------------------------------------------
-- 3. balancesheet  (from balancesheet.xlsx)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS balancesheet (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL,
    year                TEXT NOT NULL,
    equity_capital      REAL,
    reserves            REAL,
    borrowings          REAL,
    other_liabilities   REAL,
    total_liabilities   REAL,
    fixed_assets        REAL,
    cwip                REAL,
    investments         REAL,
    other_asset         REAL,
    total_assets        REAL,
    UNIQUE (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ---------------------------------------------------------------------
-- 4. cashflow  (from cashflow.xlsx)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cashflow (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL,
    year                TEXT NOT NULL,
    operating_activity  REAL,
    investing_activity  REAL,
    financing_activity  REAL,
    net_cash_flow       REAL,
    UNIQUE (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ---------------------------------------------------------------------
-- 5. analysis  (from analysis.xlsx)
-- Note: compounded_sales_growth etc. arrive as text like
-- "10 Years: 21%" — normaliser should split period + numeric value,
-- or store as text and parse downstream. Flagged for Day 02 design.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis (
    id                          INTEGER PRIMARY KEY,
    company_id                  TEXT NOT NULL,
    compounded_sales_growth     TEXT,
    compounded_profit_growth    TEXT,
    stock_price_cagr            TEXT,
    roe                         TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ---------------------------------------------------------------------
-- 6. documents  (from documents.xlsx)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL,
    year                TEXT NOT NULL,
    annual_report_url   TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ---------------------------------------------------------------------
-- 7. prosandcons  (from prosandcons.xlsx)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prosandcons (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL,
    pros                TEXT,
    cons                TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ---------------------------------------------------------------------
-- 8. sectors  (from sectors.xlsx)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sectors (
    id                    INTEGER PRIMARY KEY,
    company_id            TEXT NOT NULL UNIQUE,
    broad_sector          TEXT,
    sub_sector            TEXT,
    index_weight_pct      REAL,
    market_cap_category   TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ---------------------------------------------------------------------
-- 9. stock_prices  (from stock_prices.xlsx)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_prices (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL,
    date                TEXT NOT NULL,          -- ISO 'YYYY-MM-DD'
    open_price          REAL,
    high_price          REAL,
    low_price           REAL,
    close_price         REAL,
    volume              INTEGER,
    adjusted_close      REAL,
    UNIQUE (company_id, date),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ---------------------------------------------------------------------
-- 10. financial_ratios  (from financial_ratios.xlsx + market_cap.xlsx
--     merged on company_id + year)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS financial_ratios (
    id                          INTEGER PRIMARY KEY,
    company_id                  TEXT NOT NULL,
    year                        TEXT NOT NULL,
    net_profit_margin_pct       REAL,
    operating_profit_margin_pct REAL,
    return_on_equity_pct        REAL,
    debt_to_equity              REAL,
    interest_coverage           REAL,
    asset_turnover               REAL,
    free_cash_flow_cr           REAL,
    capex_cr                    REAL,
    earnings_per_share          REAL,
    book_value_per_share        REAL,
    dividend_payout_ratio_pct   REAL,
    total_debt_cr                REAL,
    cash_from_operations_cr     REAL,
    return_on_capital_employed_pct REAL,
    return_on_assets_pct        REAL,
    revenue_cagr_5yr            REAL,
    pat_cagr_5yr                REAL,
    eps_cagr_5yr                REAL,

composite_quality_score         REAL,
    -- merged in from market_cap.xlsx:
    market_cap_crore             REAL,
    enterprise_value_crore       REAL,
    pe_ratio                     REAL,
    pb_ratio                     REAL,
    ev_ebitda                    REAL,
    dividend_yield_pct           REAL,
    UNIQUE (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ---------------------------------------------------------------------
-- 11. peer_groups  (from peer_groups.xlsx)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS peer_groups (
    id                  INTEGER PRIMARY KEY,
    peer_group_name     TEXT NOT NULL,
    company_id          TEXT NOT NULL,
    is_benchmark        INTEGER,               -- 0/1 (SQLite has no BOOLEAN)
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ---------------------------------------------------------------------
-- Helpful indexes for common lookups (year-range queries, per-company)
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_pl_company     ON profitandloss(company_id);
CREATE INDEX IF NOT EXISTS idx_bs_company     ON balancesheet(company_id);
CREATE INDEX IF NOT EXISTS idx_cf_company     ON cashflow(company_id);
CREATE INDEX IF NOT EXISTS idx_sp_company     ON stock_prices(company_id);
CREATE INDEX IF NOT EXISTS idx_fr_company     ON financial_ratios(company_id);