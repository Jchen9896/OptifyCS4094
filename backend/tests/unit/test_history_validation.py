"""Unit tests for history date-range and price-bar validation."""

from datetime import date

import pytest

from app.core.errors import InsufficientHistoryError, InvalidDateRangeError, UnreliablePriceHistoryError
from app.market_data.base import PriceBar
from app.services.history_validation import validate_date_range, validate_price_bars


def test_validate_date_range_accepts_valid_span():
    validate_date_range(date(2026, 1, 1), date(2026, 1, 31), max_span_days=3650)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2026, 1, 31), date(2026, 1, 1)),
        (date(2026, 1, 1), date(2026, 1, 1)),
    ],
)
def test_validate_date_range_rejects_reversed_or_equal(start: date, end: date):
    with pytest.raises(InvalidDateRangeError) as raised:
        validate_date_range(start, end, max_span_days=3650)
    assert raised.value.code == "invalid_date_range"


def test_validate_date_range_rejects_span_over_max():
    with pytest.raises(InvalidDateRangeError) as raised:
        validate_date_range(date(2020, 1, 1), date(2026, 1, 1), max_span_days=30)
    assert "30" in raised.value.message


def test_validate_price_bars_accepts_valid_bars():
    validate_price_bars(
        [
            PriceBar(date=date(2026, 1, 2), open=1.0, high=2.0, low=0.5, close=1.5, volume=100),
            PriceBar(date=date(2026, 1, 3), open=1.5, high=2.5, low=1.0, close=2.0, volume=0),
        ]
    )


def test_validate_price_bars_rejects_empty_list():
    with pytest.raises(InsufficientHistoryError) as raised:
        validate_price_bars([])
    assert raised.value.code == "insufficient_history"


def test_validate_price_bars_rejects_duplicate_dates():
    bars = [
        PriceBar(date=date(2026, 1, 2), open=1.0, high=2.0, low=0.5, close=1.5, volume=100),
        PriceBar(date=date(2026, 1, 2), open=1.1, high=2.1, low=0.6, close=1.6, volume=110),
    ]
    with pytest.raises(UnreliablePriceHistoryError) as raised:
        validate_price_bars(bars)
    assert raised.value.code == "unreliable_price_history"


@pytest.mark.parametrize(
    "bar",
    [
        PriceBar(date=date(2026, 1, 2), open=0.0, high=2.0, low=0.5, close=1.5, volume=100),
        PriceBar(date=date(2026, 1, 2), open=1.0, high=2.0, low=0.5, close=float("nan"), volume=100),
        PriceBar(date=date(2026, 1, 2), open=1.0, high=0.5, low=2.0, close=1.5, volume=100),
        PriceBar(date=date(2026, 1, 2), open=1.0, high=2.0, low=0.5, close=1.5, volume=-1),
    ],
)
def test_validate_price_bars_rejects_invalid_ohlcv(bar: PriceBar):
    with pytest.raises(UnreliablePriceHistoryError):
        validate_price_bars([bar])
