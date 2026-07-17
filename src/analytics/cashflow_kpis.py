from __future__ import annotations

from typing import Optional

def free_cash_flow(
    operating_activity: float,
    investing_activity: float,
) -> float:
    """
    Calculate Free Cash Flow.

    Formula:
        Operating Activity + Investing Activity
    """
    return round(operating_activity + investing_activity, 2)


def cfo_quality_score(
    average_cfo_pat_ratio: Optional[float],
) -> Optional[str]:
    """
    Classify CFO Quality Score based on the
    5-year average CFO/PAT ratio.

    Args:
        average_cfo_pat_ratio:
            Average (Operating Cash Flow / PAT)
            over the last 5 years.

    Returns:
        "High Quality"
        "Moderate"
        "Accrual Risk"
        None if ratio is None.
    """

    if average_cfo_pat_ratio is None:
        return None

    if average_cfo_pat_ratio > 1.0:
        return "High Quality"

    if average_cfo_pat_ratio >= 0.5:
        return "Moderate"

    return "Accrual Risk"

def capex_intensity(
    investing_activity: float,
    sales: float,
) -> tuple[Optional[float], Optional[str]]:
    """
    Calculate CapEx Intensity.

    Formula:
        (abs(Investing Activity) / Sales) × 100

    Returns:
        (
            capex_intensity_pct,
            classification
        )

        Returns (None, None) if sales is zero.
    """

    if sales == 0:
        return None, None

    capex_pct = round(
        (abs(investing_activity) / sales) * 100,
        2,
    )

    if capex_pct < 3:
        label = "Asset Light"
    elif capex_pct <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return capex_pct, label

def fcf_conversion_rate(
    free_cash_flow: float,
    operating_profit: float,
) -> Optional[float]:
    """
    Calculate Free Cash Flow (FCF) Conversion Rate.

    Formula:
        (Free Cash Flow / Operating Profit) × 100

    Args:
        free_cash_flow: Free Cash Flow.
        operating_profit: Operating Profit.

    Returns:
        FCF Conversion Rate (%) rounded to 2 decimal places,
        or None if operating_profit is zero.
    """
    if operating_profit == 0:
        return None

    return round((free_cash_flow / operating_profit) * 100, 2)

def capital_allocation_pattern(
    operating_activity: float,
    investing_activity: float,
    financing_activity: float,
    high_cfo_quality: bool = False,
) -> str:
    """
    Classify capital allocation pattern based on
    the signs of CFO, CFI and CFF.

    Args:
        operating_activity: Cash flow from operating activities.
        investing_activity: Cash flow from investing activities.
        financing_activity: Cash flow from financing activities.
        high_cfo_quality: True if CFO Quality is High.

    Returns:
        Pattern label.
    """

    cfo = "+" if operating_activity >= 0 else "-"
    cfi = "+" if investing_activity >= 0 else "-"
    cff = "+" if financing_activity >= 0 else "-"

    pattern = (cfo, cfi, cff)

    if pattern == ("+", "-", "-"):
        return (
            "Shareholder Returns"
            if high_cfo_quality
            else "Reinvestor"
        )

    if pattern == ("+", "+", "-"):
        return "Liquidating Assets"

    if pattern == ("-", "+", "+"):
        return "Distress Signal"

    if pattern == ("-", "-", "+"):
        return "Growth Funded by Debt"

    if pattern == ("+", "+", "+"):
        return "Cash Accumulator"

    if pattern == ("-", "-", "-"):
        return "Pre-Revenue"

    if pattern == ("+", "-", "+"):
        return "Mixed"

    return "Unclassified"


