"""
Day 33 - PDF Company Tearsheet Template
Builds a 2-page ReportLab tearsheet per company. Charts are rendered with
matplotlib into in-memory PNG buffers and embedded as ReportLab Images -
no chart files are written to disk.

Page 1: navy header (name + ticker) -> 6 KPI tiles (2x3) -> 10yr Revenue &
        Net Profit bar chart -> ROE/ROCE dual-axis line chart
Page 2: Balance Sheet composition stacked bar -> Cash Flow bar group
        (CFO/CFI/CFF/Net, latest year) -> Pros (green) -> Cons (red) ->
        Capital Allocation badge

Judgment calls:
- 6 KPI tiles = latest-year ROE, ROCE, D/E, OPM, Revenue CAGR 5yr,
  PAT CAGR 5yr (doc lists "6 KPI tiles" without naming them; these are the
  most-referenced metrics elsewhere in the spec).
- "Cash Flow waterfall" implemented as a 4-bar grouped chart (CFO, CFI,
  CFF, Net Cash Flow) rather than a connector-line waterfall.
- Pros/Cons sourced from output/pros_cons_generated.csv, sorted by
  confidence descending, capped at 6 each so page 2 doesn't overflow.
  FALLBACK/DATA_GAP rows render in a lighter tint to stay visually
  distinguishable from genuine >60%-confidence rules.
- Capital allocation badge text comes from cashflow_intelligence.xlsx's
  capital_allocation_label column (authoritative post-Day-32 merge).
- Companies with < 3 years of profitandloss history are skipped entirely
  (charts need multi-year data) - this mirrors the Day 34 batch-skip rule,
  applied here too so single-company testing behaves the same as batch.
"""
import io
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak,
)


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
REPORTS_DIR = ROOT / "reports" / "tearsheets"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#0B1F3A")
LIGHT_GRAY = colors.HexColor("#F2F3F5")
GREEN = colors.HexColor("#1B7A3D")
RED = colors.HexColor("#B3261E")
GREEN_LIGHT = colors.HexColor("#E6F4EA")
RED_LIGHT = colors.HexColor("#FBEAE9")
GREEN_FALLBACK = colors.HexColor("#F0F6F1")
RED_FALLBACK = colors.HexColor("#FBF2F1")
BADGE_BG = colors.HexColor("#EFF3F8")

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm
USABLE_WIDTH = PAGE_W - 2 * MARGIN

MIN_YEARS_REQUIRED = 3


def load_company_bundle(conn, ticker, pros_cons_df, cf_intel_df):
    company_row = pd.read_sql(
        "SELECT id AS company_id, company_name FROM companies WHERE id = ?",
        conn, params=(ticker,),
    )
    if company_row.empty:
        return None

    pl = pd.read_sql(
        "SELECT CAST(year AS INTEGER) AS year, sales, net_profit "
        "FROM profitandloss WHERE company_id = ? ORDER BY year",
        conn, params=(ticker,),
    )
    bs = pd.read_sql(
        "SELECT CAST(year AS INTEGER) AS year, equity_capital, reserves, "
        "borrowings, other_liabilities FROM balancesheet WHERE company_id = ? ORDER BY year",
        conn, params=(ticker,),
    )
    cf = pd.read_sql(
        "SELECT CAST(year AS INTEGER) AS year, operating_activity, investing_activity, "
        "financing_activity, net_cash_flow FROM cashflow WHERE company_id = ? ORDER BY year",
        conn, params=(ticker,),
    )
    ratios = pd.read_sql(
        "SELECT CAST(year AS INTEGER) AS year, return_on_equity_pct, "
        "return_on_capital_employed_pct, debt_to_equity, operating_profit_margin_pct, "
        "revenue_cagr_5yr, pat_cagr_5yr FROM financial_ratios WHERE company_id = ? ORDER BY year",
        conn, params=(ticker,),
    )

    pros = pros_cons_df[(pros_cons_df["company_id"] == ticker) & (pros_cons_df["type"] == "pro")] \
        .sort_values("confidence_pct", ascending=False).head(6)
    cons = pros_cons_df[(pros_cons_df["company_id"] == ticker) & (pros_cons_df["type"] == "con")] \
        .sort_values("confidence_pct", ascending=False).head(6)

    intel_row = cf_intel_df[cf_intel_df["company_id"] == ticker]
    capital_label = intel_row.iloc[0]["capital_allocation_label"] if not intel_row.empty else "No Data"

    return {
        "ticker": ticker,
        "company_name": company_row.iloc[0]["company_name"],
        "pl": pl, "bs": bs, "cf": cf, "ratios": ratios,
        "pros": pros, "cons": cons,
        "capital_label": capital_label,
    }


def fmt(val, suffix="", decimals=1):
    if pd.isna(val):
        return "N/A"
    return f"{val:.{decimals}f}{suffix}"


def build_kpi_tiles(ratios):
    if ratios.empty:
        latest = {}
    else:
        latest = ratios.iloc[-1].to_dict()

    tiles = [
        ("ROE", fmt(latest.get("return_on_equity_pct"), "%")),
        ("ROCE", fmt(latest.get("return_on_capital_employed_pct"), "%")),
        ("D/E", fmt(latest.get("debt_to_equity"), "x")),
        ("OPM", fmt(latest.get("operating_profit_margin_pct"), "%")),
        ("Revenue CAGR 5yr", fmt(latest.get("revenue_cagr_5yr"), "%")),
        ("PAT CAGR 5yr", fmt(latest.get("pat_cagr_5yr"), "%")),
    ]

    label_style = ParagraphStyle("tile_label", fontSize=8, textColor=colors.grey, alignment=1)
    value_style = ParagraphStyle("tile_value", fontSize=14, textColor=NAVY, alignment=1, spaceBefore=2, fontName="Helvetica-Bold")

    cells = [[Paragraph(f"{v}", value_style), Paragraph(l, label_style)] for l, v in tiles]
    # arrange as 2 rows x 3 cols, each cell stacked value-over-label
    stacked = []
    for l, v in tiles:
        stacked.append(
            Table([[Paragraph(v, value_style)], [Paragraph(l, label_style)]],
                  colWidths=[USABLE_WIDTH / 3 - 0.2 * cm])
        )
    row1 = stacked[0:3]
    row2 = stacked[3:6]
    tile_table = Table([row1, row2], colWidths=[USABLE_WIDTH / 3] * 3)
    tile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tile_table


def chart_revenue_profit(pl):
    fig, ax = plt.subplots(figsize=(6.6, 2.6), dpi=150)
    tail = pl.tail(10)
    x = tail["year"].astype(str)
    width = 0.38
    idx = range(len(x))
    ax.bar([i - width / 2 for i in idx], tail["sales"], width, label="Revenue", color=NAVY.hexval()[2:] and "#0B1F3A")
    ax.bar([i + width / 2 for i in idx], tail["net_profit"], width, label="Net Profit", color="#4C8BF5")
    ax.set_xticks(list(idx))
    ax.set_xticklabels(x, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Rs Crore", fontsize=8)
    ax.set_title("10-Year Revenue vs Net Profit", fontsize=9, color="#0B1F3A")
    ax.legend(fontsize=7, frameon=False)
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_roe_roce(ratios):
    fig, ax1 = plt.subplots(figsize=(6.6, 2.6), dpi=150)
    tail = ratios.tail(10)
    x = tail["year"].astype(str)
    ax1.plot(x, tail["return_on_equity_pct"], color="#0B1F3A", marker="o", markersize=3, label="ROE %")
    ax1.set_ylabel("ROE %", fontsize=8, color="#0B1F3A")
    ax1.tick_params(axis="y", labelcolor="#0B1F3A", labelsize=7)
    ax1.tick_params(axis="x", labelsize=7, rotation=45)

    ax2 = ax1.twinx()
    ax2.plot(x, tail["return_on_capital_employed_pct"], color="#B3261E", marker="s", markersize=3, label="ROCE %")
    ax2.set_ylabel("ROCE %", fontsize=8, color="#B3261E")
    ax2.tick_params(axis="y", labelcolor="#B3261E", labelsize=7)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=7, frameon=False, loc="upper left")
    ax1.set_title("ROE vs ROCE Trend", fontsize=9, color="#0B1F3A")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_bs_composition(bs):
    fig, ax = plt.subplots(figsize=(6.6, 2.8), dpi=150)
    tail = bs.tail(10).copy()
    tail["equity_total"] = tail["equity_capital"].fillna(0) + tail["reserves"].fillna(0)
    x = tail["year"].astype(str)
    ax.bar(x, tail["equity_total"], label="Equity", color="#0B1F3A")
    ax.bar(x, tail["borrowings"].fillna(0), bottom=tail["equity_total"], label="Borrowings", color="#B3261E")
    bottom2 = tail["equity_total"] + tail["borrowings"].fillna(0)
    ax.bar(x, tail["other_liabilities"].fillna(0), bottom=bottom2, label="Other Liabilities", color="#4C8BF5")
    ax.set_ylabel("Rs Crore", fontsize=8)
    ax.set_title("Balance Sheet Composition", fontsize=9, color="#0B1F3A")
    ax.tick_params(labelsize=7, axis="x", rotation=45)
    ax.tick_params(labelsize=7, axis="y")
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_cashflow_latest(cf):
    fig, ax = plt.subplots(figsize=(6.6, 2.8), dpi=150)
    latest = cf.iloc[-1]
    labels = ["CFO", "CFI", "CFF", "Net Cash Flow"]
    values = [latest["operating_activity"], latest["investing_activity"],
              latest["financing_activity"], latest["net_cash_flow"]]
    bar_colors = ["#1B7A3D" if v is not None and v >= 0 else "#B3261E" for v in values]
    ax.bar(labels, values, color=bar_colors)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_ylabel("Rs Crore", fontsize=8)
    ax.set_title(f"Cash Flow Breakdown - FY{int(latest['year'])}", fontsize=9, color="#0B1F3A")
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def build_pros_cons_table(df, kind):
    is_pro = kind == "pro"
    text_color = GREEN if is_pro else RED
    bg_normal = GREEN_LIGHT if is_pro else RED_LIGHT
    bg_fallback = GREEN_FALLBACK if is_pro else RED_FALLBACK
    bullet = "+" if is_pro else "-"

    style = ParagraphStyle(
        f"{kind}_text", fontSize=8.5, textColor=colors.black, leading=11,
    )

    rows = []
    row_bgs = []
    for _, r in df.iterrows():
        is_fallback = "FALLBACK" in str(r["rule_id"]) or "DATA_GAP" in str(r["rule_id"])
        rows.append([Paragraph(f"<b>{bullet}</b> {r['text']}", style)])
        row_bgs.append(bg_fallback if is_fallback else bg_normal)

    if not rows:
        rows = [[Paragraph("No entries available.", style)]]
        row_bgs = [LIGHT_GRAY]

    tbl = Table(rows, colWidths=[USABLE_WIDTH])
    style_cmds = [
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.white),
    ]
    for i, bg in enumerate(row_bgs):
        style_cmds.append(("BACKGROUND", (0, i), (0, i), bg))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def build_capital_badge(label):
    style = ParagraphStyle("badge", fontSize=11, textColor=NAVY, alignment=1, fontName="Helvetica-Bold")
    caption = ParagraphStyle("badge_caption", fontSize=8, textColor=colors.grey, alignment=1)
    tbl = Table(
        [[Paragraph("Capital Allocation Pattern", caption)], [Paragraph(label, style)]],
        colWidths=[USABLE_WIDTH],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BADGE_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def build_header(company_name, ticker):
    name_style = ParagraphStyle("header_name", fontSize=16, textColor=colors.white, fontName="Helvetica-Bold")
    ticker_style = ParagraphStyle("header_ticker", fontSize=11, textColor=colors.HexColor("#B9C6DC"))
    tbl = Table(
        [[Paragraph(company_name, name_style), Paragraph(ticker, ticker_style)]],
        colWidths=[USABLE_WIDTH * 0.75, USABLE_WIDTH * 0.25],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (0, 0), 14),
        ("RIGHTPADDING", (1, 0), (1, 0), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return tbl


def section_heading(text, color=NAVY):
    style = ParagraphStyle("section_heading", fontSize=11, textColor=color, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=6)
    return Paragraph(text, style)


def generate_tearsheet(ticker, conn, pros_cons_df, cf_intel_df):
    bundle = load_company_bundle(conn, ticker, pros_cons_df, cf_intel_df)
    if bundle is None:
        return None, "not_found"
    if len(bundle["pl"]) < MIN_YEARS_REQUIRED:
        return None, "insufficient_history"

    out_path = REPORTS_DIR / f"{ticker}_tearsheet.pdf"
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
    )

    story = []
    story.append(build_header(bundle["company_name"], bundle["ticker"]))
    story.append(Spacer(1, 12))
    story.append(build_kpi_tiles(bundle["ratios"]))
    story.append(Spacer(1, 10))

    if not bundle["pl"].empty:
        story.append(Image(chart_revenue_profit(bundle["pl"]), width=USABLE_WIDTH, height=USABLE_WIDTH * 2.6 / 6.6))
    if not bundle["ratios"].empty:
        story.append(Spacer(1, 6))
        story.append(Image(chart_roe_roce(bundle["ratios"]), width=USABLE_WIDTH, height=USABLE_WIDTH * 2.6 / 6.6))

    story.append(PageBreak())

    if not bundle["bs"].empty:
        story.append(Image(chart_bs_composition(bundle["bs"]), width=USABLE_WIDTH, height=USABLE_WIDTH * 2.8 / 6.6))
    if not bundle["cf"].empty:
        story.append(Spacer(1, 6))
        story.append(Image(chart_cashflow_latest(bundle["cf"]), width=USABLE_WIDTH, height=USABLE_WIDTH * 2.8 / 6.6))

    story.append(section_heading("Pros", GREEN))
    story.append(build_pros_cons_table(bundle["pros"], "pro"))
    story.append(section_heading("Cons", RED))
    story.append(build_pros_cons_table(bundle["cons"], "con"))
    story.append(Spacer(1, 10))
    story.append(build_capital_badge(bundle["capital_label"]))

    doc.build(story)
    return out_path, "ok"


def main():
    test_tickers = ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"]

    conn = sqlite3.connect(DB_PATH)
    pros_cons_df = pd.read_csv(OUTPUT_DIR / "pros_cons_generated.csv")
    cf_intel_df = pd.read_excel(OUTPUT_DIR / "cashflow_intelligence.xlsx")

    print(f"Testing tearsheet generation on {len(test_tickers)} companies...\n")
    for ticker in test_tickers:
        path, status = generate_tearsheet(ticker, conn, pros_cons_df, cf_intel_df)
        if status == "ok":
            size_kb = path.stat().st_size / 1024
            flag = "OK" if size_kb >= 30 else "WARNING: below 30KB"
            print(f"  {ticker}: {path.name} ({size_kb:.1f} KB) [{flag}]")
        elif status == "not_found":
            print(f"  {ticker}: SKIPPED - not found in companies table")
        elif status == "insufficient_history":
            print(f"  {ticker}: SKIPPED - fewer than {MIN_YEARS_REQUIRED} years of P&L history")

    conn.close()
    print("\nDone. Open the PDFs in reports/tearsheets/ and visually check for overflow or blank pages.")


if __name__ == "__main__":
    main()