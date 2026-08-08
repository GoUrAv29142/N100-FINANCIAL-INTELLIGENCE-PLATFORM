"""
tests/analytics/test_cashflow.py

Unit tests for src/analytics/cashflow_kpis.py.
Sprint 2, Day 11 / Day 14 deliverable.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nifty100_dashboard.src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern,
)


class TestFreeCashFlow:
    def test_normal_case(self):
        assert free_cash_flow(500, -200) == 300.0

    def test_negative_fcf_allowed(self):
        assert free_cash_flow(100, -300) == -200.0


class TestCfoQualityScore:
    def test_high_quality(self):
        assert cfo_quality_score(1.2) == "High Quality"

    def test_moderate(self):
        assert cfo_quality_score(0.7) == "Moderate"

    def test_accrual_risk(self):
        assert cfo_quality_score(0.3) == "Accrual Risk"

    def test_none_ratio_returns_none(self):
        assert cfo_quality_score(None) is None

    def test_boundary_exactly_one(self):
        # >1.0 required for High Quality, exactly 1.0 should be Moderate
        assert cfo_quality_score(1.0) == "Moderate"

    def test_boundary_exactly_half(self):
        assert cfo_quality_score(0.5) == "Moderate"


class TestCapexIntensity:
    def test_asset_light(self):
        pct, label = capex_intensity(-20, 1000)
        assert pct == 2.0
        assert label == "Asset Light"

    def test_moderate(self):
        pct, label = capex_intensity(-50, 1000)
        assert pct == 5.0
        assert label == "Moderate"

    def test_capital_intensive(self):
        pct, label = capex_intensity(-150, 1000)
        assert pct == 15.0
        assert label == "Capital Intensive"

    def test_zero_sales_returns_none_none(self):
        pct, label = capex_intensity(-50, 0)
        assert pct is None
        assert label is None


class TestFcfConversionRate:
    def test_normal_case(self):
        assert fcf_conversion_rate(300, 500) == 60.0

    def test_zero_operating_profit_returns_none(self):
        assert fcf_conversion_rate(300, 0) is None


class TestCapitalAllocationPattern:
    def test_reinvestor(self):
        assert capital_allocation_pattern(100, -50, -20) == "Reinvestor"

    def test_shareholder_returns(self):
        assert capital_allocation_pattern(100, -50, -20, high_cfo_quality=True) == "Shareholder Returns"

    def test_liquidating_assets(self):
        assert capital_allocation_pattern(100, 50, -20) == "Liquidating Assets"

    def test_distress_signal(self):
        assert capital_allocation_pattern(-50, 30, 40) == "Distress Signal"

    def test_growth_funded_by_debt(self):
        assert capital_allocation_pattern(-50, -30, 40) == "Growth Funded by Debt"

    def test_cash_accumulator(self):
        assert capital_allocation_pattern(50, 30, 40) == "Cash Accumulator"

    def test_pre_revenue(self):
        assert capital_allocation_pattern(-50, -30, -40) == "Pre-Revenue"

    def test_mixed(self):
        assert capital_allocation_pattern(50, -30, 40) == "Mixed"