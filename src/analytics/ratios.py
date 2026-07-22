from __future__ import annotations
from typing import Optional

def net_profit_margin(net_profit: float, sales: float) -> Optional[float]:
    """
    Calculate Net Profit Margin (NPM).

    Formula:
        (Net Profit / Sales) × 100

    Args:
        net_profit: Company's net profit.
        sales: Company's total sales/revenue.

    Returns:
        Net Profit Margin (%) rounded to 2 decimal places,
        or None if sales is zero.
    """
    if sales == 0:
        return None

    return round((net_profit / sales) * 100, 2)

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def operating_profit_margin(
    operating_profit: float,
    sales: float,
    reported_opm: Optional[float] = None,
) -> Optional[float]:
    """
    Calculate Operating Profit Margin (OPM).

    Formula:
        (Operating Profit / Sales) × 100

    If a realistic reported OPM percentage exists,
    compare calculated value and log mismatch > 1%.

    Returns:
        Calculated OPM (%) rounded to 2 decimal places,
        or None if sales is zero.
    """

    if sales == 0:
        return None

    calculated_opm = round((operating_profit / sales) * 100, 2)

    # Validate only realistic percentage values
    if (
        reported_opm is not None
        and -100 <= reported_opm <= 100
        and abs(calculated_opm - reported_opm) > 1
    ):
        logger.warning(
            "OPM mismatch: calculated=%.2f, reported=%.2f",
            calculated_opm,
            reported_opm,
        )

    return calculated_opm

from typing import Optional

def return_on_equity(
    net_profit: float,
    equity_capital: float,
    reserves: float,
) -> Optional[float]:
    """
    Calculate Return on Equity (ROE).

    Formula:
        (Net Profit / (Equity Capital + Reserves)) × 100

    Args:
        net_profit: Company's net profit.
        equity_capital: Share capital.
        reserves: Company's reserves.

    Returns:
        ROE (%) rounded to 2 decimal places,
        or None if equity + reserves <= 0.
    """
    total_equity = equity_capital + reserves

    if total_equity <= 0:
        return None

    return round((net_profit / total_equity) * 100, 2)

def return_on_capital_employed(
    operating_profit: float,
    other_income: float,
    equity_capital: float,
    reserves: float,
    borrowings: float,
) -> Optional[float]:
    """
    Calculate Return on Capital Employed (ROCE).

    Formula:
        EBIT = Operating Profit + Other Income
        ROCE = (EBIT / (Equity Capital + Reserves + Borrowings)) × 100

    Returns:
        ROCE (%) rounded to 2 decimal places,
        or None if capital employed <= 0.
    """
    ebit = operating_profit + other_income
    capital_employed = equity_capital + reserves + borrowings

    if capital_employed <= 0:
        return None

    return round((ebit / capital_employed) * 100, 2)

def return_on_assets(
    net_profit: float,
    total_assets: float,
) -> Optional[float]:
    """
    Calculate Return on Assets (ROA).

    Formula:
        (Net Profit / Total Assets) × 100

    Args:
        net_profit: Company's net profit.
        total_assets: Company's total assets.

    Returns:
        ROA (%) rounded to 2 decimal places,
        or None if total_assets is zero.
    """
    if total_assets == 0:
        return None

    return round((net_profit / total_assets) * 100, 2)

def debt_to_equity(
    borrowings: float,
    equity_capital: float,
    reserves: float,
    is_financials: bool = False,
) -> tuple[Optional[float], bool]:
    """
    Calculate Debt-to-Equity ratio.

    Formula:
        Borrowings / (Equity Capital + Reserves)

    Returns:
        (de_ratio, high_leverage_flag)
    """
    if borrowings == 0:
        return 0.0, False

    total_equity = equity_capital + reserves

    if total_equity <= 0:
        return None, False

    de_ratio = round(borrowings / total_equity, 2)

    high_leverage_flag = (
        de_ratio > 5 and not is_financials
    )

    return de_ratio, high_leverage_flag

def interest_coverage(
    operating_profit: float,
    other_income: float,
    interest: float,
) -> tuple[Optional[float], Optional[str], bool]:
    """
    Calculate Interest Coverage Ratio (ICR).

    Formula:
        (Operating Profit + Other Income) / Interest

    Returns:
        tuple:
        (
            interest_coverage_ratio,
            icr_label,
            interest_warning_flag
        )
    """

    if interest == 0:
        return None, "Debt Free", False

    icr = round(
        (operating_profit + other_income) / interest,
        2
    )

    interest_warning_flag = icr < 1.5

    return icr, None, interest_warning_flag

def net_debt(
    borrowings: float,
    investments: float,
) -> float:
    """
    Calculate Net Debt.

    Formula:
        Borrowings - Investments

    Returns:
        Net Debt.
    """
    return round(borrowings - investments, 2)

def asset_turnover(
    sales: float,
    total_assets: float,
) -> Optional[float]:
    """
    Calculate Asset Turnover Ratio.

    Formula:
        Sales / Total Assets

    Args:
        sales: Company's total sales/revenue.
        total_assets: Company's total assets.

    Returns:
        Asset Turnover Ratio rounded to 2 decimal places,
        or None if total_assets is zero.
    """
    if total_assets == 0:
        return None

    return round(sales / total_assets, 2)

