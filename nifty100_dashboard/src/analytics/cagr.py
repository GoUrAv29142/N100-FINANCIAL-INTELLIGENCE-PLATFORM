from __future__ import annotations

from typing import Optional
import math


def calculate_cagr(
    start_value: float,
    end_value: float,
    years_available: int,
    required_years: int,
) -> tuple[Optional[float], Optional[str]]:
    """
    Generic CAGR calculation with Sprint 2 edge-case handling.

    Returns
    -------
    (cagr_value, flag)

    Flags:
        None
        INSUFFICIENT
        ZERO_BASE
        TURNAROUND
        DECLINE_TO_LOSS
        BOTH_NEGATIVE
    """

    if years_available < required_years:
        return None, "INSUFFICIENT"

    if start_value == 0:
        return None, "ZERO_BASE"

    if start_value > 0 and end_value < 0:
        return None, "DECLINE_TO_LOSS"

    if start_value < 0 and end_value > 0:
        return None, "TURNAROUND"

    if start_value < 0 and end_value < 0:
        return None, "BOTH_NEGATIVE"

    cagr = (
        (end_value / start_value) ** (1 / required_years)
        - 1
    ) * 100

    return round(cagr, 2), None


def revenue_cagr(
    start_sales: float,
    end_sales: float,
    years_available: int,
    required_years: int,
) -> tuple[Optional[float], Optional[str]]:
    """
    Revenue CAGR.
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
    PAT (Net Profit) CAGR.
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
    EPS CAGR.
    """

    return calculate_cagr(
        start_eps,
        end_eps,
        years_available,
        required_years,
    )