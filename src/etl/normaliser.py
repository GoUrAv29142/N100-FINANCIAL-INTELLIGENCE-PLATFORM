"""
src/etl/normaliser.py

Pure, testable normalisation functions for the nifty100-capstone ETL
pipeline. These functions take messy raw values straight out of the
source Excel files and return clean, consistent values ready for
loading into SQLite.

Design principle: every function here is a pure function (no I/O,
no side effects) so it can be unit tested in isolation, per Day 02
of Sprint 1.
"""

import re
from typing import Optional, Union


# ---------------------------------------------------------------------
# normalize_year
# ---------------------------------------------------------------------
# Observed raw formats across the 12 source files:
#   balancesheet, profitandloss, financial_ratios : "Dec 2012", "Mar 2014"
#   cashflow                                       : "Mar-13", "Mar-14"
#   market_cap, documents                          : 2019, 2024 (plain int)
#   stock_prices                                   : "2020-01-01" (full date;
#                                                      NOT handled here —
#                                                      stock_prices keeps its
#                                                      own `date` column)
#
# normalize_year() always returns a plain 4-digit int representing the
# fiscal year label (e.g. "Mar 2014" -> 2014, "Mar-13" -> 2013).
# ---------------------------------------------------------------------

_MONTH_YEAR_SPACE_RE = re.compile(r"^[A-Za-z]{3}\s+(\d{4})$")
_MONTH_YEAR_DASH_2DIGIT_RE = re.compile(r"^[A-Za-z]{3}-(\d{2})$")
_MONTH_YEAR_DASH_4DIGIT_RE = re.compile(r"^[A-Za-z]{3}-(\d{4})$")
_PLAIN_YEAR_RE = re.compile(r"^(\d{4})$")


class YearNormalizationError(ValueError):
    """Raised when a year value cannot be confidently normalized."""


def normalize_year(raw_year: Union[str, int, float, None]) -> int:
    """
    Normalize a raw year value from any of the source files into a
    plain 4-digit int.

    Examples
    --------
    >>> normalize_year("Dec 2012")
    2012
    >>> normalize_year("Mar 2014")
    2014
    >>> normalize_year("Mar-13")
    2013
    >>> normalize_year(2019)
    2019
    >>> normalize_year("2024")
    2024

    Raises
    ------
    YearNormalizationError
        If the value is None/NaN, or doesn't match any known format,
        or resolves to a year outside a sane range (1990-2035).
    """
    if raw_year is None:
        raise YearNormalizationError("year value is None")

    # Handle pandas NaN (float('nan') != float('nan'))
    if isinstance(raw_year, float) and raw_year != raw_year:
        raise YearNormalizationError("year value is NaN")

    # Plain int or float year, e.g. 2019 or 2019.0
    if isinstance(raw_year, (int, float)):
        year = int(raw_year)
        return _validate_range(year)

    if not isinstance(raw_year, str):
        raise YearNormalizationError(f"unsupported type: {type(raw_year)}")

    text = raw_year.strip()
    if not text:
        raise YearNormalizationError("year value is empty string")

    # "Dec 2012", "Mar 2014"
    m = _MONTH_YEAR_SPACE_RE.match(text)
    if m:
        return _validate_range(int(m.group(1)))

    # "Mar-2014" (4-digit dash form, seen occasionally)
    m = _MONTH_YEAR_DASH_4DIGIT_RE.match(text)
    if m:
        return _validate_range(int(m.group(1)))

    # "Mar-13" -> 2013 (pivot: always 20xx for this dataset's range)
    m = _MONTH_YEAR_DASH_2DIGIT_RE.match(text)
    if m:
        yy = int(m.group(1))
        year = 2000 + yy
        return _validate_range(year)

    # Plain "2024"
    m = _PLAIN_YEAR_RE.match(text)
    if m:
        return _validate_range(int(m.group(1)))

    raise YearNormalizationError(f"unrecognized year format: {raw_year!r}")


def _validate_range(year: int, lo: int = 1990, hi: int = 2035) -> int:
    if year < lo or year > hi:
        raise YearNormalizationError(f"year {year} outside sane range [{lo}, {hi}]")
    return year


# ---------------------------------------------------------------------
# normalize_ticker
# ---------------------------------------------------------------------
# Observed: tickers in this dataset are already mostly clean uppercase
# strings (e.g. "ABB", "HDFCBANK"), used as company_id / companies.id.
# normalize_ticker() defends against common messiness: stray whitespace,
# lowercase input, NSE/BSE suffixes, and non-alphanumeric noise.
# ---------------------------------------------------------------------

_VALID_TICKER_RE = re.compile(r"^[A-Z0-9&-]+$")
_KNOWN_SUFFIXES = (".NS", ".BO", ".NSE", ".BSE")


class TickerNormalizationError(ValueError):
    """Raised when a ticker value cannot be confidently normalized."""


def normalize_ticker(raw_ticker: Optional[str]) -> str:
    """
    Normalize a raw ticker/company_id value: strip whitespace, uppercase,
    strip known exchange suffixes.

    Examples
    --------
    >>> normalize_ticker("  abb ")
    'ABB'
    >>> normalize_ticker("HDFCBANK.NS")
    'HDFCBANK'
    >>> normalize_ticker("Tcs")
    'TCS'

    Raises
    ------
    TickerNormalizationError
        If the value is None/empty, or contains characters outside
        A-Z0-9, '&', '-' after cleaning (NSE tickers legitimately
        include these, e.g. "M&M", "BAJAJ-AUTO").
    """
    if raw_ticker is None:
        raise TickerNormalizationError("ticker value is None")

    if not isinstance(raw_ticker, str):
        raise TickerNormalizationError(f"unsupported type: {type(raw_ticker)}")

    text = raw_ticker.strip().upper()
    if not text:
        raise TickerNormalizationError("ticker value is empty string")

    for suffix in _KNOWN_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break

    text = text.strip()

    if not text:
        raise TickerNormalizationError("ticker value empty after cleaning")

    if not _VALID_TICKER_RE.match(text):
        raise TickerNormalizationError(f"invalid characters in ticker: {raw_ticker!r}")

    return text