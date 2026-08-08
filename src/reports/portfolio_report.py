"""
Day 35 - Portfolio Summary PDF
One page per company (alphabetical by ticker): name, sector, top 6 KPIs,
trend arrows comparing latest year to prior year.
"""
from pathlib import Path
import sqlite3
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak


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
REPORTS_DIR = ROOT / "reports" / "portfolio"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#0B1F3A")
LIGHT_GRAY = colors.HexColor("#F2F3F5")
GREEN = colors.HexColor("#1B7A3D")
RED = colors.HexColor("#B3261E")
GREY = colors.HexColor("#6B7280")

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm
USABLE_WIDTH = PAGE_W - 2 * MARGIN

METRIC_COLS = [
    ("return_on_equity_pct", "ROE", "higher_better"),
    ("return_on_capital_employed_pct", "ROCE", "higher_better"),
    ("debt_to_equity", "D/E", "lower_better"),
    ("operating_profit_margin_pct", "OPM", "higher_better"),
    ("revenue_cagr_5yr", "Revenue CAGR 5yr", "higher_better"),
    ("pat_cagr_5yr", "PAT CAGR 5yr", "higher_better"),
]

FLAT_THRESHOLD = 0.02  # 2% relative change


def fmt(val, suffix="%", decimals=1):
    if pd.isna(val):
        return "N/A"
    return f"{val:.{decimals}f}{suffix}"


def trend_arrow(curr, prior, direction):
    if pd.isna(curr) or pd.isna(prior):
        return "N/A", GREY
    if prior == 0:
        rel_change = float("inf") if curr != 0 else 0.0
    else:
        rel_change = (curr - prior) / abs(prior)

    if abs(rel_change) < FLAT_THRESHOLD:
        return "\u2192", GREY  # right arrow

    improved = rel_change > 0 if direction == "higher_better" else rel_change < 0
    return ("\u2191", GREEN) if improved else ("\u2193", RED)


def load_data(conn):
    companies = pd.read_sql("SELECT id AS company_id, company_name FROM companies", conn)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    ratios = pd.read_sql(
        "SELECT company_id, CAST(year AS INTEGER) AS year, return_on_equity_pct, "
        "return_on_capital_employed_pct, debt_to_equity, operating_profit_margin_pct, "
        "revenue_cagr_5yr, pat_cagr_5yr FROM financial_ratios",
        conn,
    )
    return companies, sectors, ratios


def build_company_page(company_id, company_name, sector, ratio_hist):
    header_style = ParagraphStyle("ps_header", fontSize=16, textColor=colors.white, fontName="Helvetica-Bold")
    ticker_style = ParagraphStyle("ps_ticker", fontSize=11, textColor=colors.HexColor("#B9C6DC"))
    header_tbl = Table(
        [[Paragraph(company_name, header_style), Paragraph(company_id, ticker_style)]],
        colWidths=[USABLE_WIDTH * 0.75, USABLE_WIDTH * 0.25],
    )
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (0, 0), 14),
        ("RIGHTPADDING", (1, 0), (1, 0), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    sector_style = ParagraphStyle("ps_sector", fontSize=10, textColor=GREY, spaceBefore=10, spaceAfter=14)
    sector_para = Paragraph(f"Sector: {sector}", sector_style)

    if len(ratio_hist) >= 1:
        latest = ratio_hist.iloc[-1]
        prior = ratio_hist.iloc[-2] if len(ratio_hist) >= 2 else None
    else:
        latest, prior = None, None

    label_style = ParagraphStyle("kpi_label", fontSize=9, textColor=GREY, alignment=1)
    value_style = ParagraphStyle("kpi_value", fontSize=15, textColor=NAVY, alignment=1, fontName="Helvetica-Bold")
    arrow_style_base = ParagraphStyle("kpi_arrow", fontSize=13, alignment=1, fontName="Helvetica-Bold")

    cells = []
    for col, label, direction in METRIC_COLS:
        curr_val = latest[col] if latest is not None else None
        prior_val = prior[col] if prior is not None else None
        suffix = "x" if col == "debt_to_equity" else "%"
        decimals = 2 if col == "debt_to_equity" else 1
        display_val = fmt(curr_val, suffix, decimals) if curr_val is not None else "N/A"

        arrow, arrow_color = trend_arrow(curr_val, prior_val, direction) if curr_val is not None else ("N/A", GREY)
        arrow_style = ParagraphStyle(f"arrow_{col}", parent=arrow_style_base, textColor=arrow_color)

        cell = Table(
            [[Paragraph(display_val, value_style)],
             [Paragraph(arrow, arrow_style)],
             [Paragraph(label, label_style)]],
            colWidths=[USABLE_WIDTH / 3 - 0.2 * cm],
        )
        cells.append(cell)

    row1, row2 = cells[0:3], cells[3:6]
    kpi_table = Table([row1, row2], colWidths=[USABLE_WIDTH / 3] * 3)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    footnote_style = ParagraphStyle("footnote", fontSize=7.5, textColor=GREY, spaceBefore=14)
    footnote = Paragraph(
        "Trend arrows compare latest available year to the prior available year. "
        "\u2191 improved, \u2193 declined, \u2192 flat (within 2%). "
        "For D/E, a decrease is treated as improvement.",
        footnote_style,
    )

    return [header_tbl, sector_para, kpi_table, footnote]


def main():
    conn = sqlite3.connect(DB_PATH)
    companies, sectors, ratios = load_data(conn)
    conn.close()

    sector_map = dict(zip(sectors["company_id"], sectors["broad_sector"]))
    companies_sorted = companies.sort_values("company_id").reset_index(drop=True)

    out_path = REPORTS_DIR / "portfolio_summary.pdf"
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
    )

    story = []
    no_data_count = 0
    for i, row in companies_sorted.iterrows():
        company_id, company_name = row["company_id"], row["company_name"]
        sector = sector_map.get(company_id, "Unclassified")
        ratio_hist = ratios[ratios["company_id"] == company_id].sort_values("year").reset_index(drop=True)
        if ratio_hist.empty:
            no_data_count += 1

        story.extend(build_company_page(company_id, company_name, sector, ratio_hist))
        if i < len(companies_sorted) - 1:
            story.append(PageBreak())

    doc.build(story)

    size_kb = out_path.stat().st_size / 1024
    print(f"portfolio_summary.pdf -> {out_path} ({size_kb:.1f} KB)")
    print(f"Pages: {len(companies_sorted)} (one per company, alphabetical by ticker)")
    print(f"Companies with no financial_ratios data (all KPIs N/A): {no_data_count}")
    print("Done. Open the PDF and spot-check a few pages for overflow.")


if __name__ == "__main__":
    main()