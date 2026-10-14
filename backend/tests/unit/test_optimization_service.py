"""Unit tests for OptimizationService orchestration."""

from datetime import date

import pytest

from app.core.errors import InsufficientHistoryError, InvalidOptimizationInputError
from app.market_data.base import PriceBar
from app.optimization.mean_variance import MinimumVarianceStrategy
from app.optimization.service import OptimizationService
from app.services.price_history_reader import PriceHistoryBatch
from app.services.session_calendar import WeekdaySessionCalendar


class FakeReader:
    def __init__(self, batch: PriceHistoryBatch | None = None, error: Exception | None = None):
        self.batch = batch
        self.error = error

    def read_adjusted_history(self, tickers, start, end):
        if self.error is not None:
            raise self.error
        assert self.batch is not None
        return self.batch


def _bar(day: date, close: float) -> PriceBar:
    return PriceBar(date=day, open=close, high=close, low=close, close=close, volume=0)


def _service(reader: FakeReader) -> OptimizationService:
    return OptimizationService(
        reader=reader,  # type: ignore[arg-type]
        calendar=WeekdaySessionCalendar(),
        strategies={"min_variance": MinimumVarianceStrategy(1e-5)},
        annualization_factor=252.0,
        tolerance=1e-5,
        default_risk_free_rate=0.04,
        max_span_days=3650,
    )


def test_run_returns_weights_and_metrics():
    days = [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3), date(2026, 9, 4)]
    batch = PriceHistoryBatch(
        histories={
            "AAA": [_bar(day, close) for day, close in zip(days, [100, 110, 99, 108])],
            "BBB": [_bar(day, close) for day, close in zip(days, [100, 90, 99, 95])],
        },
        source="yfinance",
        interval="1d",
        adjustment_basis="split_dividend_adjusted",
        calendar="XNYS",
    )
    result = _service(FakeReader(batch)).run(
        ["AAA", "BBB"],
        date(2026, 9, 1),
        date(2026, 9, 4),
        strategy="minvar",
        max_weight=None,
        risk_free_rate=0.04,
    )

    assert result.strategy == "min_variance"
    assert abs(sum(result.weights.values()) - 1.0) < 1e-5
    assert set(result.weights) == {"AAA", "BBB"}
    assert result.volatility >= 0
    assert any("historical estimates" in item.lower() for item in result.assumptions)


def test_run_requires_two_tickers():
    with pytest.raises(InvalidOptimizationInputError):
        _service(FakeReader()).run(
            ["AAA"],
            date(2026, 9, 1),
            date(2026, 9, 4),
            strategy="min_variance",
            max_weight=None,
            risk_free_rate=None,
        )


def test_run_surfaces_missing_stored_history():
    service = _service(FakeReader(error=InsufficientHistoryError("No stored prices")))
    with pytest.raises(InsufficientHistoryError):
        service.run(
            ["AAA", "BBB"],
            date(2026, 9, 1),
            date(2026, 9, 4),
            strategy="min_variance",
            max_weight=None,
            risk_free_rate=None,
        )
