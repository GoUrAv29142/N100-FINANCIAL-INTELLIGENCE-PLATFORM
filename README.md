## Sprint 1 Status

**Status:**  Completed

### Highlights

- End-to-end ETL pipeline
- SQLite relational database
- 11 database tables
- 16 Data Quality Rules
- 38 Unit Tests
- Referential Integrity Verified
- Exploratory SQL Queries
- Manual Data Quality Review Completed

### Validation

- Companies Loaded: 92
- Foreign Key Violations: 0
- Critical Validation Errors: 0
- Unit Tests Passed: 38/38



# Nifty 100 Financial Intelligence Platform — Sprint 4 Deliverable

Streamlit dashboard (8 screens) + Valuation module, built against `data/nifty100.db`
(92 companies, FY2011–2024 fundamentals, CY2019–2024 valuation multiples).

## Setup & Run

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

The app opens at **http://localhost:8501**. Screens are auto-listed in the sidebar
from the `pages/` folder.

To regenerate the valuation output files:

```bash
python src/analytics/valuation.py
```

This writes `output/valuation_summary.xlsx` (92 rows) and `output/valuation_flags.csv`.

## Screens

| # | File | What it shows |
|---|------|----------------|
| 1 | `pages/01_home.py` | 6 KPI tiles, sector donut chart, top-5 by composite quality score, year selector |
| 2 | `pages/02_profile.py` | Ticker search, company card, 6 KPI tiles, 10-yr revenue/profit bar chart, ROE vs ROCE line chart, pros & cons |
| 3 | `pages/03_screener.py` | 10 metric sliders, 6 preset buttons, live-updating table, CSV download |
| 4 | `pages/04_peers.py` | Peer group dropdown, radar chart, side-by-side KPI table with benchmark row highlighted |
| 5 | `pages/05_trends.py` | Company search, up to 3 overlaid metrics, 10-year line chart with YoY % annotations |
| 6 | `pages/06_sectors.py` | Sector dropdown, bubble chart (Revenue × ROE × Market Cap), sector median KPI bar chart |
| 7 | `pages/07_capital.py` | Treemap of all 92 companies by 8 capital-allocation patterns, drill-down company list |
| 8 | `pages/08_reports.py` | Company search, annual report years with BSE PDF links, "Report unavailable" badge for missing links |

## Valuation Module

- **FCF Yield** = `free_cash_flow_cr / market_cap_crore × 100`
- **Sector median P/E**: computed per `broad_sector`
- **Flags**: `P/E > sector_median × 1.5` → Caution · `P/E < sector_median × 0.7` → Discount · else Fair

## Known Data Gaps (handled, not bugs)

- **SBIN** has zero rows in `financial_ratios` (upstream ETL gap). Included in
  `valuation_summary.xlsx` with N/A values rather than dropped, keeping row count at 92.
- Screens show "N/A" or graceful messages on missing/partial data instead of crashing.

## Project Structure

```
app.py
pages/01_home.py ... 08_reports.py
utils/db.py
src/analytics/valuation.py
data/nifty100.db
output/valuation_summary.xlsx, valuation_flags.csv
requirements.txt
```