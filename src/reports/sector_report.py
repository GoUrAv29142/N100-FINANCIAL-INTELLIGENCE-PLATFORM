"""
Day 34 - Sector Report Generator
Builds one PDF per broad_sector (11 total): a summary page with median
KPIs across all companies in that sector, followed by a per-company table
of 8 metrics.

Judgment calls:
- Median KPIs computed on latest-year financial_ratios rows only.
- 8 per-company metrics = ROE, ROCE, D/E, OPM, Revenue CAGR 5yr,
  PAT CAGR 5yr, CFO Quality Label, Capital Allocation Label - a mix of
  numeric ratios and the two qualitative Sprint-5 labels, since the doc
  doesn't name the exact 8.
- Companies with no financial_ratios row show "N/A" across numeric
  columns rather than being dropped from the sector list, so sector
  company counts stay accurate.
"""
import sqlite3
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def find_project_root(marker="db/nifty100.db"):
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / marker).exists():
            return current
        current = current.parent
    raise FileNotFoundError(f"Could not locate '{marker}' above {Path(__file__).resolve()}")


ROOT = find_project_root()
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
REPORTS_DIR = ROOT / "reports" / "sector"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#0B1F3A")
LIGHT_GRAY = colors.HexColor("#F2F3F5")
PAGE_SIZE = landscape(A4)
MARGIN = 1.5 * cm
USABLE_WIDTH = PAGE_SIZE[0] - 2 * MARGIN

METRIC_COLS = [
    ("company_id", "Ticker"),
    ("company_name", "Company"),
    ("return_on_equity_pct", "ROE %"),
    ("return_on_capital_employed_pct", "ROCE %"),
    ("debt_to_equity", "D/E"),
    ("operating_profit_margin_pct", "OPM %"),
    ("revenue_cagr_5yr", "Rev CAGR 5y"),
    ("cfo_quality_label", "CFO Quality"),
    ("capital_allocation_label", "Capital Pattern"),
]

MEDIAN_COLS = [
    ("return_on_equity_pct", "Median ROE %"),
    ("return_on_capital_employed_pct", "Median ROCE %"),
    ("debt_to_equity", "Median D/E"),
    ("operating_profit_margin_pct", "Median OPM %"),
    ("revenue_cagr_5yr", "Median Rev CAGR 5y"),
]


def fmt(val, decimals=1):
    if pd.isna(val):
        return "N/A"
    if isinstance(val, str):
        return val
    return f"{val:.{decimals}f}"


def load_data(conn):
    companies = pd.read_sql("SELECT id AS company_id, company_name FROM companies", conn)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    ratios = pd.read_sql(
        "SELECT company_id, CAST(year AS INTEGER) AS year, return_on_equity_pct, "
        "return_on_capital_employed_pct, debt_to_equity, operating_profit_margin_pct, "
        "revenue_cagr_5yr FROM financial_ratios",
        conn,
    )
    latest_ratios = ratios.sort_values("year").groupby("company_id").tail(1)

    cf_intel = pd.read_excel(OUTPUT_DIR / "cashflow_intelligence.xlsx")
    cf_intel = cf_intel[["company_id", "cfo_quality_label", "capital_allocation_label"]]

    merged = companies.merge(sectors, on="company_id", how="left")
    merged = merged.merge(latest_ratios, on="company_id", how="left")
    merged = merged.merge(cf_intel, on="company_id", how="left")
    merged["broad_sector"] = merged["broad_sector"].fillna("Unclassified")
    merged["cfo_quality_label"] = merged["cfo_quality_label"].fillna("No Data")
    merged["capital_allocation_label"] = merged["capital_allocation_label"].fillna("No Data")
    return merged


def build_sector_pdf(sector_name, sector_df):
    safe_name = sector_name.replace(" ", "_").replace("/", "-")
    out_path = REPORTS_DIR / f"{safe_name}_report.pdf"

    doc = SimpleDocTemplate(
        str(out_path), pagesize=PAGE_SIZE,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
    )
    story = []

    header_style = ParagraphStyle("sector_header", fontSize=18, textColor=colors.white, fontName="Helvetica-Bold")
    header_tbl = Table([[Paragraph(f"{sector_name} Sector Report", header_style)]], colWidths=[USABLE_WIDTH])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 14))

    subheading_style = ParagraphStyle("subheading", fontSize=12, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=8)
    story.append(Paragraph(f"{len(sector_df)} companies | Sector Median KPIs (latest year)", subheading_style))

    median_row = ["Metric"] + [label for _, label in MEDIAN_COLS]
    median_vals = ["Value"] + [fmt(sector_df[col].median()) for col, _ in MEDIAN_COLS]
    median_tbl = Table([median_row, median_vals], colWidths=[USABLE_WIDTH / len(median_row)] * len(median_row))
    median_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_GRAY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
    ]))
    story.append(median_tbl)
    story.append(Spacer(1, 18))

    story.append(Paragraph("Company Detail", subheading_style))

    cell_style = ParagraphStyle("cell", fontSize=7.5, leading=9, wordWrap="CJK")
    header_cells = [Paragraph(f"<b>{label}</b>", cell_style) for _, label in METRIC_COLS]
    rows = [header_cells]
    for _, r in sector_df.sort_values("company_id").iterrows():
        row = []
        for col, _ in METRIC_COLS:
            val = r[col]
            text = val if isinstance(val, str) else fmt(val)
            row.append(Paragraph(str(text), cell_style))
        rows.append(row)

    col_widths = [USABLE_WIDTH * w for w in [0.08, 0.20, 0.08, 0.08, 0.07, 0.08, 0.10, 0.15, 0.16]]
    detail_tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    detail_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ]))
    story.append(detail_tbl)

    doc.build(story)
    return out_path


def main():
    conn = sqlite3.connect(DB_PATH)
    data = load_data(conn)
    conn.close()

    sectors = sorted(data["broad_sector"].unique())
    print(f"Generating {len(sectors)} sector reports...\n")

    for sector_name in sectors:
        sector_df = data[data["broad_sector"] == sector_name]
        path = build_sector_pdf(sector_name, sector_df)
        size_kb = path.stat().st_size / 1024
        print(f"  {sector_name}: {path.name} ({len(sector_df)} companies, {size_kb:.1f} KB)")

    actual_count = len(list(REPORTS_DIR.glob("*.pdf")))
    print(f"\nExit-criteria check: expected 11 sector PDFs, found {actual_count}")
    print("Done.")


if __name__ == "__main__":
    main()