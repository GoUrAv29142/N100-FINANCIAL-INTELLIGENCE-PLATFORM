
-- notebooks/exploratory_queries.sql
-- Sprint 1 · Day 07 · 10 exploratory queries against nifty100.db



-- 1. Sanity check: row counts across all 11 tables
-- (matches output/load_audit.csv)
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL SELECT 'peer_groups', COUNT(*) FROM peer_groups;


-- 2. Top 10 companies by latest-year sales (2024)
SELECT c.id, c.company_name, pl.sales, pl.net_profit
FROM profitandloss pl
JOIN companies c ON c.id = pl.company_id
WHERE pl.year = 2024
ORDER BY pl.sales DESC
LIMIT 10;


-- 3. Companies with the strongest 5-year sales CAGR (from analysis table)
SELECT company_id, compounded_sales_growth
FROM analysis
WHERE compounded_sales_growth LIKE '5 Years%'
ORDER BY company_id;


-- 4. Sector breakdown: company count and average index weight per sector
SELECT broad_sector, COUNT(*) AS n_companies, ROUND(AVG(index_weight_pct), 2) AS avg_weight_pct
FROM sectors
GROUP BY broad_sector
ORDER BY n_companies DESC;


-- 5. Balance sheet check: companies whose latest-year total_assets vs
-- total_liabilities differ by more than 1% (should be ~0, DQ-04 rule)
SELECT company_id, year, total_assets, total_liabilities,
       ROUND(ABS(total_assets - total_liabilities) * 100.0 / total_liabilities, 2) AS pct_diff
FROM balancesheet
WHERE year = 2024
  AND ABS(total_assets - total_liabilities) * 1.0 / total_liabilities > 0.01
ORDER BY pct_diff DESC;


-- 6. Highest dividend-paying companies (latest year, dividend_payout %)
SELECT c.id, c.company_name, pl.year, pl.dividend_payout
FROM profitandloss pl
JOIN companies c ON c.id = pl.company_id
WHERE pl.year = 2024 AND pl.dividend_payout IS NOT NULL
ORDER BY pl.dividend_payout DESC
LIMIT 10;


-- 7. Bank sector OPM sanity check (surfaces the Day 06 finding: bank
-- opm_percentage values are structurally wrong, e.g. HDFCBANK, AXISBANK)
SELECT s.company_id, pl.year, pl.opm_percentage
FROM sectors s
JOIN profitandloss pl ON pl.company_id = s.company_id
WHERE s.sub_sector LIKE '%Bank%'
ORDER BY s.company_id, pl.year;


-- 8. Stock price trend: latest close price vs. 5-year-ago close, per company
SELECT company_id,
       MIN(date) AS earliest_date,
       MAX(date) AS latest_date,
       COUNT(*) AS n_months
FROM stock_prices
GROUP BY company_id
ORDER BY n_months ASC
LIMIT 10;


-- 9. Companies with thin year coverage (<5 years of P&L data) — Day 06 check
SELECT company_id, COUNT(DISTINCT year) AS n_years
FROM profitandloss
GROUP BY company_id
HAVING n_years < 5
ORDER BY n_years ASC;


-- 10. Top 10 companies by P/E ratio (2024) — value/growth screen
SELECT c.id, c.company_name, fr.pe_ratio, fr.pb_ratio, fr.return_on_equity_pct
FROM financial_ratios fr
JOIN companies c ON c.id = fr.company_id
WHERE fr.year = 2024 AND fr.pe_ratio IS NOT NULL
ORDER BY fr.pe_ratio DESC
LIMIT 10;