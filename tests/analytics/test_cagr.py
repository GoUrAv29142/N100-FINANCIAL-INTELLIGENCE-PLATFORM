"""
tests/analytics/test_cagr.py

Unit tests for src/analytics/cagr.py.
Sprint 2, Day 10 / Day 14 deliverable — covers all 6 CAGR edge cases
listed in the spec's Section 27 test reference table.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.analytics.cagr import calculate_cagr, revenue_cagr, pat_cagr, eps_cagr


class TestCalculateCagr:
    def test_normal_positive_growth(self):
        # base=100, end=161, n=5 -> CAGR approx 10.0%
        value, flag = calculate_cagr(100, 161, 5, 5)
        assert flag is None
        assert abs(value - 10.0) < 0.5

    def test_insufficient_years(self):
        value, flag = calculate_cagr(100, 200, 2, 5)
        assert value is None
        assert flag == "INSUFFICIENT"

    def test_zero_base(self):
        value, flag = calculate_cagr(0, 200, 5, 5)
        assert value is None
        assert flag == "ZERO_BASE"

    def test_turnaround_negative_to_positive(self):
        value, flag = calculate_cagr(-100, 200, 5, 5)
        assert value is None
        assert flag == "TURNAROUND"

    def test_decline_to_loss_positive_to_negative(self):
        value, flag = calculate_cagr(100, -200, 5, 5)
        assert value is None
        assert flag == "DECLINE_TO_LOSS"

    def test_both_negative(self):
        value, flag = calculate_cagr(-100, -50, 5, 5)
        assert value is None
        assert flag == "BOTH_NEGATIVE"

    def test_exact_boundary_years_available_equals_required(self):
        # years_available == required_years should NOT trigger INSUFFICIENT
        value, flag = calculate_cagr(100, 150, 3, 3)
        assert flag is None
        assert value is not None


class TestRevenueCagr:
    def test_normal_case(self):
        value, flag = revenue_cagr(1000, 2000, 5, 5)
        assert flag is None
        assert value > 0

    def test_turnaround_flag(self):
        value, flag = revenue_cagr(-500, 1000, 3, 3)
        assert value is None
        assert flag == "TURNAROUND"


class TestPatCagr:
    def test_normal_case(self):
        value, flag = pat_cagr(500, 1000, 5, 5)
        assert flag is None
        assert value > 0

    def test_zero_base_flag(self):
        value, flag = pat_cagr(0, 500, 5, 5)
        assert value is None
        assert flag == "ZERO_BASE"


class TestEpsCagr:
    def test_normal_case(self):
        value, flag = eps_cagr(10, 20, 5, 5)
        assert flag is None
        assert value > 0

    def test_both_negative_flag(self):
        value, flag = eps_cagr(-5, -2, 3, 3)
        assert value is None
        assert flag == "BOTH_NEGATIVE"