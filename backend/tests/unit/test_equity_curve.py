"""Unit tests for portfolio capital path construction."""

from datetime import date

import pytest

from app.market_data.base import PriceBar
from app.services.equity_curve import build_equity_curve


def _bar(day: date, close: float) -> PriceBar:
    return PriceBar(date=day, open=close, high=close, low=close, close=close, volume=0)


def test_equity_curve_starts_at_initial_capital_and_tracks_prices():
    days = [date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6)]
    histories = {
        "AAA": [_bar(days[0], 100), _bar(days[1], 110), _bar(days[2], 120)],
        "BBB": [_bar(days[0], 50), _bar(days[1], 50), _bar(days[2], 40)],
    }
    # Equal weights: day0=100, day1=0.5*(1.1+1.0)*100=105, day2=0.5*(1.2+0.8)*100=100
    points = build_equity_curve(histories, ["AAA", "BBB"], [0.5, 0.5], [1.0, 0.0], 100.0)

    assert points[0].current_value == pytest.approx(100.0)
    assert points[0].optimized_value == pytest.approx(100.0)
    assert points[1].current_value == pytest.approx(105.0)
    assert points[1].optimized_value == pytest.approx(110.0)
    assert points[2].current_value == pytest.approx(100.0)
    assert points[2].optimized_value == pytest.approx(120.0)
