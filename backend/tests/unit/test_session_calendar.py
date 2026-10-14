"""Check real exchange schedules and their use in stored-price calculations."""

from datetime import date, datetime, timezone

import pytest

from app.core.errors import AppError
from app.market_data.base import PriceBar
from app.market_data.session_calendar import ExchangeSessionCalendar
from app.services.stored_calculation_service import (
    PriceHistoryMetadata,
    StoredCalculationService,
    StoredPriceHistory,
)


@pytest.fixture
def calendar():
    return ExchangeSessionCalendar("XNYS")


@pytest.mark.parametrize("start,end,expected", [
    (date(2026, 10, 5), date(2026, 10, 7), (date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7))),
    (date(2026, 10, 9), date(2026, 10, 12), (date(2026, 10, 9), date(2026, 10, 12))),
    (date(2026, 12, 24), date(2026, 12, 28), (date(2026, 12, 24), date(2026, 12, 28))),
    (date(2026, 4, 2), date(2026, 4, 6), (date(2026, 4, 2), date(2026, 4, 6))),
    (date(2026, 12, 25), date(2026, 12, 25), ()),
    (date(2026, 10, 10), date(2026, 10, 11), ()),
])
def test_calendar_returns_only_trading_dates_with_inclusive_bounds(calendar, start, end, expected):
    assert calendar.name == "XNYS"
    assert calendar.sessions_in_range(start, end) == expected


def test_unknown_calendar_is_reported_as_an_application_error():
    with pytest.raises(AppError) as error:
        ExchangeSessionCalendar("UNKNOWN_EXCHANGE")
    assert error.value.code == "unsupported_calendar"
    assert error.value.status_code == 422


@pytest.mark.parametrize("start,end", [
    (date(2000, 1, 1), date(2026, 10, 7)),
    (date(2026, 10, 5), date(2100, 1, 1)),
])
def test_dates_outside_the_loaded_schedule_are_rejected(calendar, start, end):
    with pytest.raises(AppError, match="supports dates") as error:
        calendar.sessions_in_range(start, end)
    assert error.value.code == "unsupported_period"
    assert error.value.status_code == 422


def test_reversed_period_is_rejected(calendar):
    with pytest.raises(AppError) as error:
        calendar.sessions_in_range(date(2026, 10, 7), date(2026, 10, 5))
    assert error.value.code == "invalid_calculation_input"


def test_real_calendar_prevents_return_across_a_missing_trading_day(calendar):
    metadata = PriceHistoryMetadata(
        source="fixture", retrieved_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
        adjustment_basis="split_dividend_adjusted", interval="1d", exchange="NMS", calendar="XNYS",
    )
    prices = tuple(
        PriceBar(date(2026, 10, day), close, close, close, close, 0)
        for day, close in [(5, 100), (7, 120), (8, 132), (9, 118.8)]
    )

    class Reader:
        def read_adjusted_history(self, _tickers, _start, _end):
            return {"AAA": StoredPriceHistory(prices, metadata)}

    result = StoredCalculationService(Reader(), calendar, 252).calculate(
        ["AAA"], date(2026, 10, 5), date(2026, 10, 9)
    )

    assert result.returns.intervals == (
        (date(2026, 10, 7), date(2026, 10, 8)),
        (date(2026, 10, 8), date(2026, 10, 9)),
    )
    assert result.returns.daily_mean_returns == pytest.approx((0.0,), abs=1e-12)
    assert result.returns.dropped_interval_count == 2
