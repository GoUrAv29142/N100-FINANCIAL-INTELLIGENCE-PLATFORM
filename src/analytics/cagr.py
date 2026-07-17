from __future__ import annotations

from typing import Optional

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

def revenue_cagr(
    start_sales: float,
    end_sales: float,
    years_available: int,
    required_years: int,
) -> tuple[Optional[float], Optional[str]]:
    """
    Calculate Revenue CAGR.

    Returns:
        (revenue_cagr, flag)
    """
    return calculate_cagr(
        start_sales,
        end_sales,
        years_available,
        required_years,
    )


def revenue_cagr(
    start_sales: float,
    end_sales: float,
    years_available: int,
    required_years: int,
) -> tuple[Optional[float], Optional[str]]:
    """
    Calculate Revenue CAGR.

    Returns:
        (revenue_cagr, flag)
    """
    return calculate_cagr(
        start_sales,
        end_sales,
        years_available,
        required_years,
    )


def pat_cagr(
    start_profit: float,
    end_profit: float,
    years_available: int,
    required_years: int,
) -> tuple[Optional[float], Optional[str]]:
    """
    Calculate PAT (Net Profit) CAGR.

    Returns:
        (pat_cagr, flag)
    """
    return calculate_cagr(
        start_profit,
        end_profit,
        years_available,
        required_years,
    )

def eps_cagr(
    start_eps: float,
    end_eps: float,
    years_available: int,
    required_years: int,
) -> tuple[Optional[float], Optional[str]]:
    """
    Calculate EPS CAGR.

    Returns:
        (eps_cagr, flag)
    """
    return calculate_cagr(
        start_eps,
        end_eps,
        years_available,
        required_years,
    )