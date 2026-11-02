"""Unit tests for OptimizationService orchestration."""

from datetime import date

import pytest

from app.core.errors import InsufficientHistoryError, InvalidOptimizationInputError
from app.market_data.base import PriceBar
from app.optimization.mean_variance import MaxSharpeStrategy, MinimumVarianceStrategy
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


def _two_stock_batch() -> PriceHistoryBatch:
    """Four days of prices for two stocks, so three daily returns."""
    days = [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3), date(2026, 9, 4)]
    return PriceHistoryBatch(
        histories={
            "AAA": [_bar(day, close) for day, close in zip(days, [100, 110, 99, 108])],
            "BBB": [_bar(day, close) for day, close in zip(days, [100, 90, 99, 95])],
        },
        source="yfinance",
        interval="1d",
        adjustment_basis="split_dividend_adjusted",
        calendar="XNYS",
    )


# The low default minimums let the test batches with three returns run.
def _service(
    reader: FakeReader,
    min_observations: int = 3,
    min_observations_per_stock: int = 1,
) -> OptimizationService:
    return OptimizationService(
        reader=reader,  # type: ignore[arg-type]
        calendar=WeekdaySessionCalendar(),
        strategies=[MinimumVarianceStrategy(1e-5, "CLARABEL"), MaxSharpeStrategy(1e-5, "CLARABEL")],
        annualization_factor=252.0,
        tolerance=1e-5,
        default_risk_free_rate=0.04,
        max_span_days=3650,
        initial_capital=100_000.0,
        min_observations=min_observations,
        min_observations_per_stock=min_observations_per_stock,
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
        strategy="min_variance",
        max_weight=None,
        risk_free_rate=0.04,
        current_weights=[0.5, 0.5],
    )

    assert result.strategy == "min_variance"
    assert abs(sum(result.weights.values()) - 1.0) < 1e-5
    assert set(result.weights) == {"AAA", "BBB"}
    assert result.volatility >= 0
    assert result.initial_capital == 100_000.0
    assert len(result.equity_curve) >= 2
    assert result.equity_curve[0].current_value == pytest.approx(100_000.0)
    assert result.current_expected_return is not None
    assert result.current_volatility >= 0
    assert any("historical estimates" in item.lower() for item in result.assumptions)
    assert "Maximum weight per stock: None." in result.assumptions


def test_run_uses_request_initial_capital():
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
        strategy="min_variance",
        max_weight=None,
        risk_free_rate=0.04,
        current_weights=[0.5, 0.5],
        initial_capital=50_000.0,
    )

    assert result.initial_capital == 50_000.0
    assert result.equity_curve[0].current_value == pytest.approx(50_000.0)


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


def test_run_max_sharpe_is_not_worse_than_the_current_allocation():
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
        strategy="max_sharpe",
        max_weight=None,
        risk_free_rate=0.04,
        current_weights=[0.5, 0.5],
    )

    assert result.strategy == "max_sharpe"
    assert abs(sum(result.weights.values()) - 1.0) < 1e-5
    # The current allocation follows the rules, so max Sharpe must be at least as good.
    assert result.sharpe_ratio >= result.current_sharpe_ratio - 1e-5


def test_run_rejects_an_unknown_strategy_and_lists_the_names():
    with pytest.raises(InvalidOptimizationInputError, match="min_variance, max_sharpe"):
        _service(FakeReader()).run(
            ["AAA", "BBB"],
            date(2026, 9, 1),
            date(2026, 9, 4),
            strategy="mvo",
            max_weight=None,
            risk_free_rate=None,
        )


@pytest.mark.parametrize(
    ("min_observations", "min_observations_per_stock", "required"),
    [(5, 1, 5), (2, 3, 6)],
    ids=["the minimum decides", "the minimum per stock decides"],
)
def test_run_rejects_too_few_returns(min_observations, min_observations_per_stock, required):
    # The batch has three returns for two stocks.
    service = _service(FakeReader(_two_stock_batch()), min_observations, min_observations_per_stock)

    with pytest.raises(InsufficientHistoryError, match=f"only 3 trading days .* at least {required}:"):
        service.run(
            ["AAA", "BBB"],
            date(2026, 9, 1),
            date(2026, 9, 4),
            strategy="min_variance",
            max_weight=None,
            risk_free_rate=None,
        )
