"""
tests/analytics/test_ratios.py

Unit tests for src/analytics/ratios.py.
Sprint 2, Day 08-09 / Day 14 deliverable.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nifty100_dashboard.src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    debt_to_equity,
    interest_coverage,
    net_debt,
    asset_turnover,
)


class TestNetProfitMargin:
    def test_normal_case(self):
        assert net_profit_margin(100, 1000) == 10.0

    def test_zero_sales_returns_none(self):
        assert net_profit_margin(100, 0) is None

    def test_negative_profit_allowed(self):
        assert net_profit_margin(-50, 1000) == -5.0


class TestOperatingProfitMargin:
    def test_normal_case(self):
        assert operating_profit_margin(200, 1000) == 20.0

    def test_zero_sales_returns_none(self):
        assert operating_profit_margin(200, 0) is None

    def test_opm_mismatch_does_not_raise(self):
        # Should still return the calculated value even with a mismatched
        # reported_opm, just logs a warning internally.
        result = operating_profit_margin(200, 1000, reported_opm=50.0)
        assert result == 20.0


class TestReturnOnEquity:
    def test_normal_case(self):
        assert return_on_equity(100, 400, 100) == 20.0

    def test_negative_equity_returns_none(self):
        assert return_on_equity(100, -400, 100) is None

    def test_zero_equity_returns_none(self):
        assert return_on_equity(100, 0, 0) is None


class TestReturnOnCapitalEmployed:
    def test_normal_case(self):
        # EBIT = 100+20=120, capital_employed = 400+100+500=1000
        assert return_on_capital_employed(100, 20, 400, 100, 500) == 12.0

    def test_zero_capital_employed_returns_none(self):
        assert return_on_capital_employed(100, 20, 0, 0, 0) is None


class TestReturnOnAssets:
    def test_normal_case(self):
        assert return_on_assets(100, 1000) == 10.0

    def test_zero_assets_returns_none(self):
        assert return_on_assets(100, 0) is None


class TestDebtToEquity:
    def test_normal_case(self):
        de, flag = debt_to_equity(500, 400, 100)
        assert de == 1.0
        assert flag is False

    def test_debt_free_returns_zero(self):
        de, flag = debt_to_equity(0, 400, 100)
        assert de == 0.0
        assert flag is False

    def test_negative_equity_returns_none(self):
        de, flag = debt_to_equity(500, -400, 100)
        assert de is None
        assert flag is False

    def test_high_leverage_flag_non_financials(self):
        de, flag = debt_to_equity(3000, 400, 100, is_financials=False)
        assert de == 6.0
        assert flag is True

    def test_high_leverage_flag_suppressed_for_financials(self):
        de, flag = debt_to_equity(3000, 400, 100, is_financials=True)
        assert de == 6.0
        assert flag is False


class TestInterestCoverage:
    def test_normal_case(self):
        icr, label, warn = interest_coverage(200, 20, 50)
        assert icr == 4.4
        assert label is None
        assert warn is False

    def test_debt_free_returns_none_with_label(self):
        icr, label, warn = interest_coverage(200, 20, 0)
        assert icr is None
        assert label == "Debt Free"
        assert warn is False

    def test_low_icr_triggers_warning_flag(self):
        icr, label, warn = interest_coverage(50, 0, 50)
        assert icr == 1.0
        assert warn is True


class TestNetDebt:
    def test_normal_case(self):
        assert net_debt(500, 100) == 400.0

    def test_net_cash_positive_company(self):
        assert net_debt(0, 100) == -100.0


class TestAssetTurnover:
    def test_normal_case(self):
        assert asset_turnover(1000, 500) == 2.0

    def test_zero_assets_returns_none(self):
        assert asset_turnover(1000, 0) is None