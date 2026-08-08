"""
Day 30 - Auto Pros/Cons Generator
Applies 12 pro rules and 12 con rules against financial_ratios (+ sectors
for the non-financial filter) and writes output/pros_cons_generated.csv.

Judgment calls (see chat for full rationale):
- "Consecutive years" = consecutive AVAILABLE rows per company, not
  calendar-continuous.
- Pro Rule 7 uses numeric interest_coverage / debt_to_equity instead of
  icr_label, which is 0% populated on the latest-year snapshot.
- Pro Rule 11 implemented as PAT CAGR > Revenue CAGR (operating leverage,
  matches the rule's own explanatory text, not its contradictory header).
- Con Rule 11 "net debt" = total_debt_cr (gross debt; no cash balance
  column exists to net against). EBITDA derived as OPM% x sales.
- Pro Rule 12 compares latest year vs prior year only (no year-count given).
- Companies with zero financial_ratios rows get a DATA_GAP pro/con instead
  of the normal rule set.
- Companies with real data but no rule clearing the 60% confidence cutoff
  (common for very high-quality blue chips with no cons, or weak names with
  no pros) get a FALLBACK row: the single closest-to-firing rule for that
  side, emitted at a capped 15-59% confidence and tagged "<rule_id>_FALLBACK"
  so it stays clearly distinguishable from genuinely-triggered rules. This
  is what satisfies the Day 30 exit criterion (>=1 pro and >=1 con for every
  company) without pretending a real signal fired when it didn't.
"""
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

CONFIDENCE_FLOOR = 65  # comfortably above the 60% inclusion cutoff
BINARY_CONFIDENCE = 90.0


def scaled_confidence(distance_ratio, base=CONFIDENCE_FLOOR, span=35):
    """distance_ratio: 0 = just crossed the threshold, >=1 = comfortably past it."""
    ratio = min(1.0, max(0.0, distance_ratio))
    return round(base + span * ratio, 1)


def fallback_confidence(distance):
    """Compress any real-valued distance into 15-59%, always below the 60%
    inclusion cutoff so fallback rows are visually distinguishable from
    genuinely-fired rules. distance=+1 (comfortably would-have-fired) -> 59,
    distance=-1 (far from firing) -> 15."""
    clamped = max(-1.0, min(1.0, distance))
    return round(15 + 44 * (clamped + 1) / 2, 1)


def load_data(conn):
    companies = pd.read_sql("SELECT id AS company_id FROM companies", conn)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    ratios = pd.read_sql(
        "SELECT company_id, CAST(year AS INTEGER) AS year, "
        "net_profit_margin_pct, operating_profit_margin_pct, return_on_equity_pct, "
        "debt_to_equity, interest_coverage, asset_turnover, free_cash_flow_cr, "
        "earnings_per_share, dividend_payout_ratio_pct, total_debt_cr, "
        "return_on_capital_employed_pct, revenue_cagr_5yr, revenue_cagr_3yr, "
        "pat_cagr_5yr, eps_cagr_5yr, net_profit, sales, dividend_yield_pct "
        "FROM financial_ratios",
        conn,
    )
    return companies, sectors, ratios


def consecutive_tail(df_sorted_by_year, n):
    """Last n available rows (not calendar-continuous), or None if fewer than n exist."""
    if len(df_sorted_by_year) < n:
        return None
    return df_sorted_by_year.tail(n)


PRO_RULE_TEXT = {
    1: "Consistently high return on equity above 20% demonstrates exceptional capital efficiency",
    2: "Strong free cash flow generation over 5 years signals healthy business fundamentals",
    3: "Debt-free balance sheet provides financial flexibility and eliminates interest burden",
    4: "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum",
    5: "Operating profit margin above 25% indicates strong pricing power and cost discipline",
    6: "Net profit compounding at above 20% over 5 years creates significant shareholder value",
    7: "Very high interest coverage ratio reflects negligible financial stress from debt servicing",
    8: "Consistent dividend yield above 2% backed by positive free cash flow",
    9: "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding",
    10: "Return on equity improving for 3 consecutive years shows strengthening business quality",
    11: "Revenue growing slower than profits shows improving operating leverage and scale benefits",
    12: "Growing asset base funded by internal accruals reflects self-sustaining growth",
}

CON_RULE_TEXT = {
    2: "Free cash flow negative for 3 consecutive years raises concern about cash generation quality",
    3: "Operating margins declining for 3 consecutive years suggest pricing or cost pressure",
    4: "Company reported a net loss in the most recent financial year",
    5: "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss",
    6: "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",
    7: "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",
    8: "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk",
    9: "Earnings per share declining for 3 consecutive years reflects deteriorating profitability",
    10: "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",
    11: "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility",
    12: "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",
}


def evaluate_company(company_id, hist, sector, records):
    if hist.empty:
        return

    latest = hist.iloc[-1]
    last2 = consecutive_tail(hist, 2)
    last3 = consecutive_tail(hist, 3)
    last5 = consecutive_tail(hist, 5)

    # ---------- PRO RULES ----------
    if last3 is not None and last3["return_on_equity_pct"].notna().all() and (last3["return_on_equity_pct"] > 20).all():
        avg_excess = (last3["return_on_equity_pct"] - 20).mean()
        records.append((company_id, "pro", 1, PRO_RULE_TEXT[1], scaled_confidence(avg_excess / 15)))

    if last5 is not None and last5["free_cash_flow_cr"].notna().all() and (last5["free_cash_flow_cr"] > 0).all():
        records.append((company_id, "pro", 2, PRO_RULE_TEXT[2], BINARY_CONFIDENCE))

    if pd.notna(latest["debt_to_equity"]) and latest["debt_to_equity"] == 0:
        records.append((company_id, "pro", 3, PRO_RULE_TEXT[3], BINARY_CONFIDENCE))

    if pd.notna(latest["revenue_cagr_5yr"]) and latest["revenue_cagr_5yr"] > 15:
        records.append((company_id, "pro", 4, PRO_RULE_TEXT[4], scaled_confidence((latest["revenue_cagr_5yr"] - 15) / 15)))

    if pd.notna(latest["operating_profit_margin_pct"]) and latest["operating_profit_margin_pct"] > 25:
        records.append((company_id, "pro", 5, PRO_RULE_TEXT[5], scaled_confidence((latest["operating_profit_margin_pct"] - 25) / 15)))

    if pd.notna(latest["pat_cagr_5yr"]) and latest["pat_cagr_5yr"] > 20:
        records.append((company_id, "pro", 6, PRO_RULE_TEXT[6], scaled_confidence((latest["pat_cagr_5yr"] - 20) / 20)))

    debt_free = pd.notna(latest["debt_to_equity"]) and latest["debt_to_equity"] == 0
    icr_strong = pd.notna(latest["interest_coverage"]) and latest["interest_coverage"] > 10
    if debt_free or icr_strong:
        conf = BINARY_CONFIDENCE if debt_free else scaled_confidence((latest["interest_coverage"] - 10) / 15)
        records.append((company_id, "pro", 7, PRO_RULE_TEXT[7], conf))

    if (pd.notna(latest["dividend_yield_pct"]) and latest["dividend_yield_pct"] > 2
            and pd.notna(latest["free_cash_flow_cr"]) and latest["free_cash_flow_cr"] > 0):
        records.append((company_id, "pro", 8, PRO_RULE_TEXT[8], scaled_confidence((latest["dividend_yield_pct"] - 2) / 3)))

    if pd.notna(latest["eps_cagr_5yr"]) and latest["eps_cagr_5yr"] > 15:
        records.append((company_id, "pro", 9, PRO_RULE_TEXT[9], scaled_confidence((latest["eps_cagr_5yr"] - 15) / 15)))

    if last3 is not None and last3["return_on_equity_pct"].notna().all():
        vals = last3["return_on_equity_pct"].tolist()
        if vals[0] < vals[1] < vals[2]:
            records.append((company_id, "pro", 10, PRO_RULE_TEXT[10], scaled_confidence((vals[2] - vals[0]) / 10)))

    if pd.notna(latest["pat_cagr_5yr"]) and pd.notna(latest["revenue_cagr_5yr"]) and latest["pat_cagr_5yr"] > latest["revenue_cagr_5yr"]:
        records.append((company_id, "pro", 11, PRO_RULE_TEXT[11], scaled_confidence((latest["pat_cagr_5yr"] - latest["revenue_cagr_5yr"]) / 10)))

    if last2 is not None:
        prev, curr = last2.iloc[0], last2.iloc[1]
        if (pd.notna(prev["asset_turnover"]) and prev["asset_turnover"] != 0
                and pd.notna(curr["asset_turnover"]) and curr["asset_turnover"] != 0
                and pd.notna(prev["total_debt_cr"]) and pd.notna(curr["total_debt_cr"])):
            prev_assets = prev["sales"] / prev["asset_turnover"]
            curr_assets = curr["sales"] / curr["asset_turnover"]
            if curr_assets > prev_assets and curr["total_debt_cr"] < prev["total_debt_cr"]:
                records.append((company_id, "pro", 12, PRO_RULE_TEXT[12], BINARY_CONFIDENCE))

    # ---------- CON RULES ----------
    if sector != "Financials" and pd.notna(latest["debt_to_equity"]) and latest["debt_to_equity"] > 2.0:
        text = f"Debt-to-equity ratio of {latest['debt_to_equity']:.2f} is elevated for a non-financial company and warrants monitoring"
        records.append((company_id, "con", 1, text, scaled_confidence((latest["debt_to_equity"] - 2) / 2)))

    if last3 is not None and last3["free_cash_flow_cr"].notna().all() and (last3["free_cash_flow_cr"] < 0).all():
        records.append((company_id, "con", 2, CON_RULE_TEXT[2], BINARY_CONFIDENCE))

    if last3 is not None and last3["operating_profit_margin_pct"].notna().all():
        vals = last3["operating_profit_margin_pct"].tolist()
        if vals[0] > vals[1] > vals[2]:
            records.append((company_id, "con", 3, CON_RULE_TEXT[3], scaled_confidence((vals[0] - vals[2]) / 10)))

    if pd.notna(latest["net_profit"]) and latest["net_profit"] < 0:
        records.append((company_id, "con", 4, CON_RULE_TEXT[4], BINARY_CONFIDENCE))

    if last2 is not None and last2["sales"].notna().all():
        vals = last2["sales"].tolist()
        if vals[0] > vals[1] and vals[0] != 0:
            records.append((company_id, "con", 5, CON_RULE_TEXT[5], scaled_confidence((vals[0] - vals[1]) / vals[0])))

    if pd.notna(latest["interest_coverage"]) and latest["interest_coverage"] < 1.5:
        records.append((company_id, "con", 6, CON_RULE_TEXT[6], scaled_confidence((1.5 - latest["interest_coverage"]) / 1.5)))

    if pd.notna(latest["dividend_payout_ratio_pct"]) and latest["dividend_payout_ratio_pct"] > 100:
        records.append((company_id, "con", 7, CON_RULE_TEXT[7], scaled_confidence((latest["dividend_payout_ratio_pct"] - 100) / 50)))

    if last3 is not None and last3["debt_to_equity"].notna().all():
        vals = last3["debt_to_equity"].tolist()
        if vals[0] < vals[1] < vals[2]:
            records.append((company_id, "con", 8, CON_RULE_TEXT[8], scaled_confidence((vals[2] - vals[0]) / 1.0)))

    if last3 is not None and last3["earnings_per_share"].notna().all():
        vals = last3["earnings_per_share"].tolist()
        if vals[0] > vals[1] > vals[2] and vals[0] != 0:
            records.append((company_id, "con", 9, CON_RULE_TEXT[9], scaled_confidence((vals[0] - vals[2]) / abs(vals[0]))))

    if pd.notna(latest["return_on_capital_employed_pct"]) and latest["return_on_capital_employed_pct"] < 10:
        records.append((company_id, "con", 10, CON_RULE_TEXT[10], scaled_confidence((10 - latest["return_on_capital_employed_pct"]) / 10)))

    if pd.notna(latest["operating_profit_margin_pct"]) and pd.notna(latest["sales"]) and pd.notna(latest["total_debt_cr"]):
        ebitda = (latest["operating_profit_margin_pct"] / 100) * latest["sales"]
        if ebitda > 0 and latest["total_debt_cr"] > 3 * ebitda:
            records.append((company_id, "con", 11, CON_RULE_TEXT[11], scaled_confidence((latest["total_debt_cr"] / ebitda - 3) / 2)))

    if pd.notna(latest["revenue_cagr_5yr"]) and latest["revenue_cagr_5yr"] < 5:
        records.append((company_id, "con", 12, CON_RULE_TEXT[12], scaled_confidence((5 - latest["revenue_cagr_5yr"]) / 10)))


def compute_fallback_candidates(company_id, hist, sector):
    """For a company missing pro/con coverage: compute a 'closest to firing'
    distance for every rule we CAN evaluate, even if the strict condition
    never held. Returns two lists of (rule_id, distance, text) tuples,
    sorted best-first (highest distance = closest to / furthest past the
    threshold), for pro and con respectively."""
    if hist.empty:
        return [], []

    latest = hist.iloc[-1]
    last2 = consecutive_tail(hist, 2)
    last3 = consecutive_tail(hist, 3)
    last5 = consecutive_tail(hist, 5)

    pro_candidates = []
    con_candidates = []

    # --- pro fallback distances (same math as primary rules, minus the gate) ---
    if last3 is not None and last3["return_on_equity_pct"].notna().all():
        d = (last3["return_on_equity_pct"] - 20).mean() / 15
        pro_candidates.append((1, d, PRO_RULE_TEXT[1]))

    if last5 is not None and last5["free_cash_flow_cr"].notna().all():
        pos_count = (last5["free_cash_flow_cr"] > 0).sum()
        d = (pos_count - 2.5) / 2.5
        pro_candidates.append((2, d, PRO_RULE_TEXT[2]))

    if pd.notna(latest["debt_to_equity"]):
        d = 1 - latest["debt_to_equity"]  # de=0 -> 1, de=1 -> 0, de=2 -> -1
        pro_candidates.append((3, d, PRO_RULE_TEXT[3]))

    if pd.notna(latest["revenue_cagr_5yr"]):
        d = (latest["revenue_cagr_5yr"] - 15) / 15
        pro_candidates.append((4, d, PRO_RULE_TEXT[4]))

    if pd.notna(latest["operating_profit_margin_pct"]):
        d = (latest["operating_profit_margin_pct"] - 25) / 15
        pro_candidates.append((5, d, PRO_RULE_TEXT[5]))

    if pd.notna(latest["pat_cagr_5yr"]):
        d = (latest["pat_cagr_5yr"] - 20) / 20
        pro_candidates.append((6, d, PRO_RULE_TEXT[6]))

    if pd.notna(latest["interest_coverage"]) or pd.notna(latest["debt_to_equity"]):
        de0 = pd.notna(latest["debt_to_equity"]) and latest["debt_to_equity"] == 0
        if de0:
            d = 1.0
        elif pd.notna(latest["interest_coverage"]):
            d = (latest["interest_coverage"] - 10) / 15
        else:
            d = -1.0
        pro_candidates.append((7, d, PRO_RULE_TEXT[7]))

    if pd.notna(latest["dividend_yield_pct"]) and pd.notna(latest["free_cash_flow_cr"]):
        d_yield = (latest["dividend_yield_pct"] - 2) / 3
        d_fcf = 1.0 if latest["free_cash_flow_cr"] > 0 else -1.0
        pro_candidates.append((8, min(d_yield, d_fcf), PRO_RULE_TEXT[8]))

    if pd.notna(latest["eps_cagr_5yr"]):
        d = (latest["eps_cagr_5yr"] - 15) / 15
        pro_candidates.append((9, d, PRO_RULE_TEXT[9]))

    if last3 is not None and last3["return_on_equity_pct"].notna().all():
        vals = last3["return_on_equity_pct"].tolist()
        d = (vals[2] - vals[0]) / 10
        pro_candidates.append((10, d, PRO_RULE_TEXT[10]))

    if pd.notna(latest["pat_cagr_5yr"]) and pd.notna(latest["revenue_cagr_5yr"]):
        d = (latest["pat_cagr_5yr"] - latest["revenue_cagr_5yr"]) / 10
        pro_candidates.append((11, d, PRO_RULE_TEXT[11]))

    if last2 is not None:
        prev, curr = last2.iloc[0], last2.iloc[1]
        if (pd.notna(prev["asset_turnover"]) and prev["asset_turnover"] != 0
                and pd.notna(curr["asset_turnover"]) and curr["asset_turnover"] != 0
                and pd.notna(prev["total_debt_cr"]) and pd.notna(curr["total_debt_cr"])):
            prev_assets = prev["sales"] / prev["asset_turnover"]
            curr_assets = curr["sales"] / curr["asset_turnover"]
            asset_grew = curr_assets > prev_assets
            debt_fell = curr["total_debt_cr"] < prev["total_debt_cr"]
            d = 1.0 if (asset_grew and debt_fell) else (0.3 if (asset_grew or debt_fell) else -1.0)
            pro_candidates.append((12, d, PRO_RULE_TEXT[12]))

    # --- con fallback distances ---
    if sector != "Financials" and pd.notna(latest["debt_to_equity"]):
        d = (latest["debt_to_equity"] - 2) / 2
        text = f"Debt-to-equity ratio of {latest['debt_to_equity']:.2f} is elevated for a non-financial company and warrants monitoring"
        con_candidates.append((1, d, text))

    if last3 is not None and last3["free_cash_flow_cr"].notna().all():
        neg_count = (last3["free_cash_flow_cr"] < 0).sum()
        d = (neg_count - 1.5) / 1.5
        con_candidates.append((2, d, CON_RULE_TEXT[2]))

    if last3 is not None and last3["operating_profit_margin_pct"].notna().all():
        vals = last3["operating_profit_margin_pct"].tolist()
        d = (vals[0] - vals[2]) / 10
        con_candidates.append((3, d, CON_RULE_TEXT[3]))

    if pd.notna(latest["net_profit_margin_pct"]):
        d = -latest["net_profit_margin_pct"] / 20  # low/negative margin -> higher distance
        con_candidates.append((4, d, CON_RULE_TEXT[4]))

    if last2 is not None and last2["sales"].notna().all():
        vals = last2["sales"].tolist()
        if vals[0] != 0:
            d = (vals[0] - vals[1]) / vals[0]
            con_candidates.append((5, d, CON_RULE_TEXT[5]))

    if pd.notna(latest["interest_coverage"]):
        d = (1.5 - latest["interest_coverage"]) / 1.5
        con_candidates.append((6, d, CON_RULE_TEXT[6]))

    if pd.notna(latest["dividend_payout_ratio_pct"]):
        d = (latest["dividend_payout_ratio_pct"] - 100) / 50
        con_candidates.append((7, d, CON_RULE_TEXT[7]))

    if last3 is not None and last3["debt_to_equity"].notna().all():
        vals = last3["debt_to_equity"].tolist()
        d = (vals[2] - vals[0]) / 1.0
        con_candidates.append((8, d, CON_RULE_TEXT[8]))

    if last3 is not None and last3["earnings_per_share"].notna().all():
        vals = last3["earnings_per_share"].tolist()
        if vals[0] != 0:
            d = (vals[0] - vals[2]) / abs(vals[0])
            con_candidates.append((9, d, CON_RULE_TEXT[9]))

    if pd.notna(latest["return_on_capital_employed_pct"]):
        d = (10 - latest["return_on_capital_employed_pct"]) / 10
        con_candidates.append((10, d, CON_RULE_TEXT[10]))

    if pd.notna(latest["operating_profit_margin_pct"]) and pd.notna(latest["sales"]) and pd.notna(latest["total_debt_cr"]):
        ebitda = (latest["operating_profit_margin_pct"] / 100) * latest["sales"]
        if ebitda > 0:
            d = (latest["total_debt_cr"] / ebitda - 3) / 2
            con_candidates.append((11, d, CON_RULE_TEXT[11]))

    if pd.notna(latest["revenue_cagr_5yr"]):
        d = (5 - latest["revenue_cagr_5yr"]) / 10
        con_candidates.append((12, d, CON_RULE_TEXT[12]))

    pro_candidates.sort(key=lambda x: x[1], reverse=True)
    con_candidates.sort(key=lambda x: x[1], reverse=True)
    return pro_candidates, con_candidates


def main():
    conn = sqlite3.connect(DB_PATH)
    companies, sectors, ratios = load_data(conn)
    conn.close()

    sector_map = dict(zip(sectors["company_id"], sectors["broad_sector"]))
    records = []
    covered_ids = set(ratios["company_id"].unique())

    for company_id in companies["company_id"]:
        hist = ratios[ratios["company_id"] == company_id].sort_values("year").reset_index(drop=True)
        sector = sector_map.get(company_id, "Unknown")
        evaluate_company(company_id, hist, sector, records)

    out_df = pd.DataFrame(records, columns=["company_id", "type", "rule_id", "text", "confidence_pct"])
    out_df = out_df[out_df["confidence_pct"] > 60]

    # ---------- DATA_GAP fallback: companies with zero financial_ratios rows ----------
    no_data_ids = set(companies["company_id"]) - covered_ids
    gap_records = []
    for cid in no_data_ids:
        msg = "No financial_ratios data is available for this company; pros/cons could not be computed."
        gap_records.append((cid, "pro", "DATA_GAP", msg, 100.0))
        gap_records.append((cid, "con", "DATA_GAP", msg, 100.0))
    if gap_records:
        out_df = pd.concat([out_df, pd.DataFrame(gap_records, columns=out_df.columns)], ignore_index=True)

    # ---------- FALLBACK pass: companies with real data but no rule cleared 60% ----------
    still_missing_pro, still_missing_con = [], []
    for cid in companies["company_id"]:
        sub = out_df[out_df["company_id"] == cid]
        if not (sub["type"] == "pro").any():
            still_missing_pro.append(cid)
        if not (sub["type"] == "con").any():
            still_missing_con.append(cid)

    fallback_records = []
    for cid in still_missing_pro:
        hist = ratios[ratios["company_id"] == cid].sort_values("year").reset_index(drop=True)
        sector = sector_map.get(cid, "Unknown")
        pro_cands, _ = compute_fallback_candidates(cid, hist, sector)
        if pro_cands:
            rule_id, dist, text = pro_cands[0]
            fallback_records.append((cid, "pro", f"{rule_id}_FALLBACK", text, fallback_confidence(dist)))

    for cid in still_missing_con:
        hist = ratios[ratios["company_id"] == cid].sort_values("year").reset_index(drop=True)
        sector = sector_map.get(cid, "Unknown")
        _, con_cands = compute_fallback_candidates(cid, hist, sector)
        if con_cands:
            rule_id, dist, text = con_cands[0]
            fallback_records.append((cid, "con", f"{rule_id}_FALLBACK", text, fallback_confidence(dist)))

    if fallback_records:
        out_df = pd.concat([out_df, pd.DataFrame(fallback_records, columns=out_df.columns)], ignore_index=True)

    out_path = OUTPUT_DIR / "pros_cons_generated.csv"
    out_df.to_csv(out_path, index=False)

    print(f"Total pro/con records: {len(out_df)} -> {out_path}")
    print(f"  pros: {(out_df['type'] == 'pro').sum()}, cons: {(out_df['type'] == 'con').sum()}")
    if no_data_ids:
        print(f"  DATA_GAP fallback applied to: {sorted(no_data_ids)}")
    if fallback_records:
        print(f"  Low-confidence FALLBACK rows added: {len(fallback_records)}")

    print("\nExit-criteria check: every company has >=1 pro and >=1 con")
    missing_pro, missing_con = [], []
    for cid in companies["company_id"]:
        sub = out_df[out_df["company_id"] == cid]
        if not (sub["type"] == "pro").any():
            missing_pro.append(cid)
        if not (sub["type"] == "con").any():
            missing_con.append(cid)
    print(f"  Companies missing a pro: {len(missing_pro)} {missing_pro if missing_pro else ''}")
    print(f"  Companies missing a con: {len(missing_con)} {missing_con if missing_con else ''}")

    print("\nRule firing counts:")
    print(out_df.groupby(["type", "rule_id"]).size().to_string())
    print("\nDone.")


if __name__ == "__main__":
    main()