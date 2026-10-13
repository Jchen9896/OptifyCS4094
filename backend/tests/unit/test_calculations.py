"""Check daily returns with known prices and missing trading sessions."""

from datetime import date

import pytest

from app.core.errors import AppError
from app.market_data.base import PriceBar
from app.services.calculation_service import calculate_daily_returns


SESSIONS = [date(2026, 10, day) for day in (5, 6, 7, 8)]


def price(day: date, close: float) -> PriceBar:
    return PriceBar(date=day, open=close, high=close, low=close, close=close, volume=0)


def test_returns_match_hand_calculated_gains_and_losses():
    bars = [price(day, close) for day, close in zip(SESSIONS[:3], (100, 110, 99))]

    result = calculate_daily_returns(bars, SESSIONS[:3])

    assert [item.value for item in result] == pytest.approx([0.10, -0.10])
    assert [(item.start_date, item.end_date) for item in result] == [
        (SESSIONS[0], SESSIONS[1]),
        (SESSIONS[1], SESSIONS[2]),
    ]


def test_price_order_does_not_change_returns_or_modify_input():
    bars = [price(SESSIONS[2], 99), price(SESSIONS[0], 100), price(SESSIONS[1], 110)]
    original = bars.copy()

    result = calculate_daily_returns(bars, SESSIONS[:3])

    assert [item.value for item in result] == pytest.approx([0.10, -0.10])
    assert bars == original


def test_missing_session_removes_both_affected_intervals():
    bars = [price(SESSIONS[0], 100), price(SESSIONS[2], 120), price(SESSIONS[3], 126)]

    result = calculate_daily_returns(bars, SESSIONS)

    assert len(result) == 1
    assert (result[0].start_date, result[0].end_date) == (SESSIONS[2], SESSIONS[3])
    assert result[0].value == pytest.approx(0.05)


@pytest.mark.parametrize(
    "sessions",
    [
        [date(2026, 10, 9), date(2026, 10, 12)],  # Friday to Monday.
        [date(2026, 12, 24), date(2026, 12, 28)],  # Christmas and a weekend.
    ],
)
def test_market_closures_do_not_break_a_daily_return(sessions):
    result = calculate_daily_returns(
        [price(sessions[0], 100), price(sessions[1], 110)], sessions
    )

    assert len(result) == 1
    assert result[0].value == pytest.approx(0.10)


@pytest.mark.parametrize("closes", [[], [100]])
def test_short_history_has_no_returns(closes):
    bars = [price(day, close) for day, close in zip(SESSIONS, closes)]

    assert calculate_daily_returns(bars, SESSIONS) == []


def test_empty_period_has_no_returns():
    assert calculate_daily_returns([], []) == []


def test_constant_prices_have_zero_returns():
    result = calculate_daily_returns([price(day, 100) for day in SESSIONS], SESSIONS)

    assert [item.value for item in result] == [0.0, 0.0, 0.0]


@pytest.mark.parametrize("close", [0, -1, float("nan"), float("inf"), -float("inf")])
def test_invalid_close_is_rejected(close):
    with pytest.raises(AppError, match="finite and greater than zero") as error:
        calculate_daily_returns([price(SESSIONS[0], close)], SESSIONS)

    assert error.value.code == "invalid_price_history"
    assert error.value.status_code == 422


def test_duplicate_price_date_is_rejected():
    with pytest.raises(AppError, match="More than one price"):
        calculate_daily_returns([price(SESSIONS[0], 100), price(SESSIONS[0], 101)], SESSIONS)


@pytest.mark.parametrize("day", [date(2026, 10, 4), date(2026, 10, 9)])
def test_price_outside_expected_sessions_is_rejected(day):
    with pytest.raises(AppError, match="not a trading session"):
        calculate_daily_returns([price(day, 100)], SESSIONS)


@pytest.mark.parametrize("sessions", [SESSIONS[::-1], [SESSIONS[0], SESSIONS[0]]])
def test_invalid_session_order_is_rejected(sessions):
    with pytest.raises(AppError, match="unique and ordered"):
        calculate_daily_returns([], sessions)


def test_return_overflow_is_rejected():
    with pytest.raises(AppError, match="return.*not finite"):
        calculate_daily_returns(
            [price(SESSIONS[0], 1e-300), price(SESSIONS[1], 1e300)], SESSIONS[:2]
        )
