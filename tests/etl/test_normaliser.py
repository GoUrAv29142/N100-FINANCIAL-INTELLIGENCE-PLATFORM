"""
tests/etl/test_normaliser.py

Unit tests for src/etl/normaliser.py — normalize_year() and
normalize_ticker(). Sprint 1, Day 02 deliverable: 35+ ETL unit tests.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nifty100_dashboard.src.etl.normaliser import (
    normalize_year,
    normalize_ticker,
    YearNormalizationError,
    TickerNormalizationError,
)


# ---------------------------------------------------------------------
# normalize_year — 22 tests
# ---------------------------------------------------------------------

class TestNormalizeYear:

    # --- valid formats ---
    def test_month_space_year_dec(self):
        assert normalize_year("Dec 2012") == 2012

    def test_month_space_year_mar(self):
        assert normalize_year("Mar 2014") == 2014

    def test_month_dash_2digit(self):
        assert normalize_year("Mar-13") == 2013

    def test_month_dash_2digit_dec(self):
        assert normalize_year("Dec-22") == 2022

    def test_month_dash_4digit(self):
        assert normalize_year("Mar-2014") == 2014

    def test_plain_int(self):
        assert normalize_year(2019) == 2019

    def test_plain_float(self):
        assert normalize_year(2019.0) == 2019

    def test_plain_string_year(self):
        assert normalize_year("2024") == 2024

    def test_string_with_whitespace(self):
        assert normalize_year("  2020  ") == 2020

    def test_lowercase_month(self):
        assert normalize_year("mar 2015") == 2015

    def test_mixed_case_month(self):
        assert normalize_year("MaR 2016") == 2016

    def test_boundary_year_low(self):
        assert normalize_year(1990) == 1990

    def test_boundary_year_high(self):
        assert normalize_year(2035) == 2035

    def test_dash_2digit_far_future_rejected(self):
        # 2-digit years pivot to 20xx; "99" -> 2099 is out of the sane
        # range [1990, 2035] for this dataset, so it should be rejected.
        with pytest.raises(YearNormalizationError):
            normalize_year("Jun-99")

    def test_dash_2digit_realistic_pivots_correctly(self):
        # A realistic 2-digit year within range should pivot correctly.
        assert normalize_year("Jun-10") == 2010

    # --- invalid / rejected values ---
    def test_none_raises(self):
        with pytest.raises(YearNormalizationError):
            normalize_year(None)

    def test_nan_raises(self):
        with pytest.raises(YearNormalizationError):
            normalize_year(float("nan"))

    def test_ttm_raises(self):
        with pytest.raises(YearNormalizationError):
            normalize_year("TTM")

    def test_garbage_string_raises(self):
        with pytest.raises(YearNormalizationError):
            normalize_year("xyz")

    def test_empty_string_raises(self):
        with pytest.raises(YearNormalizationError):
            normalize_year("")

    def test_whitespace_only_raises(self):
        with pytest.raises(YearNormalizationError):
            normalize_year("   ")

    def test_year_out_of_range_low_raises(self):
        with pytest.raises(YearNormalizationError):
            normalize_year(1899)

    def test_year_out_of_range_high_raises(self):
        with pytest.raises(YearNormalizationError):
            normalize_year(2099)

    def test_unsupported_type_raises(self):
        with pytest.raises(YearNormalizationError):
            normalize_year([2020])

    def test_malformed_month_format_raises(self):
        with pytest.raises(YearNormalizationError):
            normalize_year("Mar 2023 15")  # matches real bad data seen in AMBUJACEM row


# ---------------------------------------------------------------------
# normalize_ticker — 15 tests
# ---------------------------------------------------------------------

class TestNormalizeTicker:

    def test_strip_whitespace(self):
        assert normalize_ticker("  abb ") == "ABB"

    def test_uppercase_conversion(self):
        assert normalize_ticker("tcs") == "TCS"

    def test_mixed_case(self):
        assert normalize_ticker("Tcs") == "TCS"

    def test_already_clean(self):
        assert normalize_ticker("HDFCBANK") == "HDFCBANK"

    def test_ns_suffix_stripped(self):
        assert normalize_ticker("HDFCBANK.NS") == "HDFCBANK"

    def test_bo_suffix_stripped(self):
        assert normalize_ticker("TCS.BO") == "TCS"

    def test_hyphen_preserved(self):
        assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"

    def test_ampersand_preserved(self):
        assert normalize_ticker("M&M") == "M&M"

    def test_lowercase_with_hyphen(self):
        assert normalize_ticker("bajaj-auto") == "BAJAJ-AUTO"

    def test_none_raises(self):
        with pytest.raises(TickerNormalizationError):
            normalize_ticker(None)

    def test_empty_string_raises(self):
        with pytest.raises(TickerNormalizationError):
            normalize_ticker("")

    def test_whitespace_only_raises(self):
        with pytest.raises(TickerNormalizationError):
            normalize_ticker("   ")

    def test_unsupported_type_raises(self):
        with pytest.raises(TickerNormalizationError):
            normalize_ticker(12345)

    def test_invalid_characters_raises(self):
        with pytest.raises(TickerNormalizationError):
            normalize_ticker("TCS@#$")

    def test_nse_suffix_lowercase_stripped(self):
        assert normalize_ticker("infy.ns") == "INFY"