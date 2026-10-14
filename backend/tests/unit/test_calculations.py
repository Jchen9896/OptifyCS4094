"""Unit tests for daily returns, averages, and covariance."""

from datetime import date

import pytest

from app.core.errors import InsufficientHistoryError, InvalidPriceHistoryError
from app.market_data.base import PriceBar
from app.services.calculation_service import (
    calculate_daily_returns,
    calculate_portfolio_statistics,
)


def _bar(day: date, close: float) -> PriceBar:
    return PriceBar(date=day, open=close, high=close, low=close, close=close, volume=0)


SESSIONS = [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3)]


def test_calculate_daily_returns_simple_values():
    prices = [_bar(SESSIONS[0], 100), _bar(SESSIONS[1], 110), _bar(SESSIONS[2], 99)]
    returns = calculate_daily_returns(prices, SESSIONS)
    assert [item.value for item in returns] == pytest.approx([0.1, -0.1])


def test_calculate_daily_returns_skips_missing_session_price():
    prices = [_bar(SESSIONS[0], 100), _bar(SESSIONS[2], 110)]
    returns = calculate_daily_returns(prices, SESSIONS)
    assert returns == []


def test_calculate_daily_returns_rejects_duplicate_dates():
    prices = [_bar(SESSIONS[0], 100), _bar(SESSIONS[0], 101)]
    with pytest.raises(InvalidPriceHistoryError):
        calculate_daily_returns(prices, SESSIONS)


def test_portfolio_statistics_hand_calculated_fixture():
    # AAA=[100,110,99], BBB=[100,90,99] over three sessions (calculations.md).
    histories = {
        "AAA": [_bar(SESSIONS[0], 100), _bar(SESSIONS[1], 110), _bar(SESSIONS[2], 99)],
        "BBB": [_bar(SESSIONS[0], 100), _bar(SESSIONS[1], 90), _bar(SESSIONS[2], 99)],
    }
    result = calculate_portfolio_statistics(histories, ["AAA", "BBB"], SESSIONS, 252.0)
    assert result.observation_count == 2
    assert result.annualized_mean_returns == pytest.approx([0.0, 0.0], abs=1e-12)
    assert result.annualized_covariance[0][0] == pytest.approx(5.04, abs=1e-12)
    assert result.annualized_covariance[1][1] == pytest.approx(5.04, abs=1e-12)
    assert result.annualized_covariance[0][1] == pytest.approx(-5.04, abs=1e-12)


def test_portfolio_statistics_requires_two_aligned_returns():
    histories = {
        "AAA": [_bar(SESSIONS[0], 100), _bar(SESSIONS[1], 110)],
        "BBB": [_bar(SESSIONS[0], 100), _bar(SESSIONS[1], 90)],
    }
    with pytest.raises(InsufficientHistoryError):
        calculate_portfolio_statistics(histories, ["AAA", "BBB"], SESSIONS[:2], 252.0)
