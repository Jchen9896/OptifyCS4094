"""Unit tests for OptimizationService orchestration."""

from datetime import date

import pytest

from app.core.config import Settings
from app.core.errors import InsufficientHistoryError, InvalidOptimizationInputError
from app.market_data.base import PriceBar
from app.optimization.black_litterman import BlackLittermanEstimator
from app.optimization.mean_variance import (
    MaxSharpeStrategy,
    MinimumVarianceStrategy,
    TargetReturnStrategy,
    TargetRiskStrategy,
)
from app.optimization.service import OptimizationService
from app.services.price_history_reader import PriceHistoryBatch
from app.services.session_calendar import WeekdaySessionCalendar

# The values in config.py, not from a local .env file. Refer to Decisions 005 and 009.
TOLERANCE = Settings.model_fields["optimization_tolerance"].default
SOLVER = Settings.model_fields["optimization_solver"].default
EQUITY_RISK_PREMIUM = Settings.model_fields["equity_risk_premium"].default
TAU = Settings.model_fields["black_litterman_tau"].default
MARKET_TICKER = Settings.model_fields["market_proxy_ticker"].default


class FakeReader:
    def __init__(self, batch: PriceHistoryBatch | None = None, error: Exception | None = None):
        self.batch = batch
        self.error = error

    def read_adjusted_history(self, tickers, start, end):
        if self.error is not None:
            raise self.error
        assert self.batch is not None
        return self.batch


class FakeMarketHistory:
    def __init__(self):
        self.calls = []

    def get_or_fetch_history(self, symbol, start, end):
        self.calls.append((symbol, start, end))


def _bar(day: date, close: float) -> PriceBar:
    return PriceBar(date=day, open=close, high=close, low=close, close=close, volume=0)


def _two_stock_batch() -> PriceHistoryBatch:
    """Four days of prices for two stocks and the market index, so three daily returns."""
    days = [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3), date(2026, 9, 4)]
    return PriceHistoryBatch(
        histories={
            "AAA": [_bar(day, close) for day, close in zip(days, [100, 110, 99, 108])],
            "BBB": [_bar(day, close) for day, close in zip(days, [100, 90, 99, 95])],
            MARKET_TICKER: [_bar(day, close) for day, close in zip(days, [100, 101, 99, 102])],
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
    market_history: FakeMarketHistory | None = None,
) -> OptimizationService:
    return OptimizationService(
        reader=reader,  # type: ignore[arg-type]
        calendar=WeekdaySessionCalendar(),
        strategies=[
            MinimumVarianceStrategy(TOLERANCE, SOLVER),
            MaxSharpeStrategy(TOLERANCE, SOLVER),
            TargetReturnStrategy(TOLERANCE, SOLVER),
            TargetRiskStrategy(TOLERANCE, SOLVER),
        ],
        market_history=FakeMarketHistory() if market_history is None else market_history,  # type: ignore[arg-type]
        return_estimator=BlackLittermanEstimator(EQUITY_RISK_PREMIUM, TAU, MARKET_TICKER),
        annualization_factor=252.0,
        tolerance=TOLERANCE,
        default_risk_free_rate=0.04,
        max_span_days=3650,
        initial_capital=100_000.0,
        min_observations=min_observations,
        min_observations_per_stock=min_observations_per_stock,
    )


def test_run_returns_weights_and_metrics():
    market_history = FakeMarketHistory()
    result = _service(FakeReader(_two_stock_batch()), market_history=market_history).run(
        ["AAA", "BBB"],
        date(2026, 9, 1),
        date(2026, 9, 4),
        strategy="min_variance",
        max_weight=None,
        risk_free_rate=0.04,
        current_weights=[0.5, 0.5],
    )

    assert result.strategy == "min_variance"
    assert abs(sum(result.weights.values()) - 1.0) < TOLERANCE
    # The market index is loaded once for the expected returns, and it gets no weight.
    assert market_history.calls == [(MARKET_TICKER, date(2026, 9, 1), date(2026, 9, 4))]
    assert set(result.weights) == {"AAA", "BBB"}
    assert any(item.startswith("Expected returns: Black–Litterman.") for item in result.assumptions)
    assert result.volatility >= 0
    assert result.initial_capital == 100_000.0
    assert len(result.equity_curve) >= 2
    assert result.equity_curve[0].current_value == pytest.approx(100_000.0)
    assert result.current_expected_return is not None
    assert result.current_volatility >= 0
    assert any("historical estimates" in item.lower() for item in result.assumptions)
    assert "Maximum weight per stock: None." in result.assumptions
    assert [row.symbol for row in result.asset_stats] == ["AAA", "BBB"]
    assert all(row.annualized_return is not None for row in result.asset_stats)
    assert all(row.annualized_volatility is not None for row in result.asset_stats)
    assert "Required holdings: none." in result.assumptions


def test_run_honors_required_min_weights():
    # Unconstrained min-variance already keeps AAA above a small floor on this fixture,
    # so assert the contract (≥ floor) and the assumptions line rather than equality.
    result = _service(FakeReader(_two_stock_batch())).run(
        ["AAA", "BBB"],
        date(2026, 9, 1),
        date(2026, 9, 4),
        strategy="min_variance",
        max_weight=None,
        risk_free_rate=0.04,
        current_weights=[0.5, 0.5],
        min_weights=[0.25, 0.0],
    )

    assert result.weights["AAA"] >= 0.25 - TOLERANCE
    assert "Required holdings: AAA ≥ 25%." in result.assumptions


def test_run_uses_request_initial_capital():
    result = _service(FakeReader(_two_stock_batch())).run(
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
    result = _service(FakeReader(_two_stock_batch())).run(
        ["AAA", "BBB"],
        date(2026, 9, 1),
        date(2026, 9, 4),
        strategy="max_sharpe",
        max_weight=None,
        risk_free_rate=0.04,
        current_weights=[0.5, 0.5],
    )

    assert result.strategy == "max_sharpe"
    assert abs(sum(result.weights.values()) - 1.0) < TOLERANCE
    # The current allocation follows the rules, so max Sharpe must be at least as good.
    assert result.sharpe_ratio >= result.current_sharpe_ratio - TOLERANCE


def test_run_gives_the_target_to_the_strategy_and_shows_it():
    # With the Black–Litterman returns of the test prices, a 10% target is above the minimum-variance
    # return (about 5.6%) and below the highest return (about 24.5%), so the target decides the weights.
    result = _service(FakeReader(_two_stock_batch())).run(
        ["AAA", "BBB"],
        date(2026, 9, 1),
        date(2026, 9, 4),
        strategy="target_return",
        max_weight=None,
        risk_free_rate=0.04,
        target_return=0.1,
    )

    assert result.expected_return == pytest.approx(0.1, abs=TOLERANCE)
    assert "Target return: at least 10%." in result.assumptions


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
# The market index is added only once, and the minimum counts only the selected stocks.
@pytest.mark.parametrize(
    "tickers",
    [["AAA", "BBB"], ["AAA", MARKET_TICKER]],
    ids=["two stocks", "with the market index"],
)
def test_run_rejects_too_few_returns(min_observations, min_observations_per_stock, required, tickers):
    # The batch has three returns for two stocks.
    service = _service(FakeReader(_two_stock_batch()), min_observations, min_observations_per_stock)

    with pytest.raises(InsufficientHistoryError, match=f"only 3 trading days .* at least {required}:"):
        service.run(
            tickers,
            date(2026, 9, 1),
            date(2026, 9, 4),
            strategy="min_variance",
            max_weight=None,
            risk_free_rate=None,
        )
