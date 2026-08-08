## Sprint 5 Retro — Known Issues Carried Forward

1. **Sector count: 10, not 11.** sectors.xlsx / the sectors table has no
   "Conglomerates / Other" bucket. ~4 companies that the project doc's
   reference table (section 6.1) assigns to Conglomerates are currently
   classified under Financials (23 companies vs the doc's expected 19).
   Sector reports generated for all 10 sectors present in the data;
   AC criterion "11 sector PDFs" cannot be met until the sectors table
   is corrected upstream (Sprint 1/3 data issue, not a Sprint 5 defect).
   Action: flag to team lead for sectors.xlsx correction before final
   sign-off, or accept 10 as the actual sector count going forward.

2. **JIOFIN skipped from tearsheets** (insufficient_history — <3 years
   of P&L data). Legitimate skip: JIOFIN demerged from Reliance in 2023,
   so it genuinely lacks 3+ years of standalone financials. Logged in
   output/skipped_tearsheets.csv per spec. Included normally in
   portfolio_summary.pdf with N/A KPIs, since that report has no
   3-year minimum.

3. SBIN missing from financial_ratios / capital_allocation.csv — ROOT CAUSE
   CONFIRMED: data/raw/core/balancesheet.xlsx has zero rows for SBIN
   (1,312 total rows, 0 for SBIN), despite SBIN having 12 rows in both
   profitandloss.xlsx and cashflow.xlsx. This is a genuine source-data
   gap, not an ETL or Ratio Engine bug — verified by reading the raw
   Excel file directly. ROE, D/E, ROCE, and Asset Turnover cannot be
   computed for SBIN without balance sheet data. Per project doc R-01/
   DQ-16, SBIN is excluded from clustering (Day 36) and any KPI relying
   on balance sheet fields, pending manual sourcing of SBIN's balance
   sheet from a public filing (out of scope for this sprint).