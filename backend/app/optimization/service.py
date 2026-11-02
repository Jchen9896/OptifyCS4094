"""Assemble stored-history statistics and run an optimization strategy."""

from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import InsufficientHistoryError, InvalidOptimizationInputError
from app.optimization.base import OptimizationStrategy
from app.optimization.mean_variance import (
    MaxSharpeStrategy,
    MinimumVarianceStrategy,
    TargetReturnStrategy,
    TargetRiskStrategy,
)
from app.optimization.validation import validate_optimizer_input
from app.repositories.price_repository import PriceRepository
from app.schemas.optimization import EquityCurvePointSchema, OptimizationResult, OptimizerInput
from app.services.calculation_service import calculate_portfolio_statistics
from app.services.equity_curve import build_equity_curve
from app.services.history_validation import validate_date_range
from app.services.price_history_reader import StoredPriceHistoryReader
from app.services.session_calendar import SessionCalendar, WeekdaySessionCalendar


class OptimizationService:
    """Read stored prices, calculate statistics, and return allocation weights."""

    def __init__(
        self,
        reader: StoredPriceHistoryReader,
        calendar: SessionCalendar,
        strategies: list[OptimizationStrategy],
        *,
        annualization_factor: float,
        tolerance: float,
        default_risk_free_rate: float,
        max_span_days: int,
        initial_capital: float,
        min_observations: int,
        min_observations_per_stock: int,
    ) -> None:
        self._reader = reader
        self._calendar = calendar
        # A request selects a strategy by its `name`, for example "min_variance" or "max_sharpe".
        self._strategies = {item.name: item for item in strategies}
        self._annualization_factor = annualization_factor
        self._tolerance = tolerance
        self._default_risk_free_rate = default_risk_free_rate
        self._max_span_days = max_span_days
        self._initial_capital = initial_capital
        self._min_observations = min_observations
        self._min_observations_per_stock = min_observations_per_stock

    def run(
        self,
        tickers: list[str],
        start_date,
        end_date,
        *,
        strategy: str,
        max_weight: float | None,
        risk_free_rate: float | None,
        current_weights: list[float] | None = None,
        initial_capital: float | None = None,
        target_return: float | None = None,
        target_volatility: float | None = None,
    ) -> OptimizationResult:
        """Optimize weights for `tickers` over the stored history in the date range.

        The targets go to the strategy. Only the target strategies use them.
        """
        validate_date_range(start_date, end_date, self._max_span_days)
        normalized = [ticker.strip().upper() for ticker in tickers]
        if len(normalized) < 2:
            raise InvalidOptimizationInputError("Select at least two tickers for optimization.")
        if len(normalized) != len(set(normalized)):
            raise InvalidOptimizationInputError("Each ticker may appear only once.")

        selected = self._strategies.get(strategy)
        if selected is None:
            raise InvalidOptimizationInputError(
                f"Strategy '{strategy}' is not supported. Use one of: {', '.join(self._strategies)}."
            )
        risk_free = (
            self._default_risk_free_rate if risk_free_rate is None else risk_free_rate
        )
        capital = self._initial_capital if initial_capital is None else float(initial_capital)
        if capital <= 0:
            raise InvalidOptimizationInputError("Initial portfolio value must be greater than zero.")

        batch = self._reader.read_adjusted_history(normalized, start_date, end_date)
        sessions = self._calendar.sessions_in_range(start_date, end_date)
        stats = calculate_portfolio_statistics(
            batch.histories,
            normalized,
            sessions,
            self._annualization_factor,
        )
        # Too few returns give an unreliable covariance matrix (Decision 005, "Minimum history").
        stock_count = len(stats.tickers)
        required = max(self._min_observations, self._min_observations_per_stock * stock_count)
        if stats.observation_count < required:
            raise InsufficientHistoryError(
                f"These {stock_count} stocks share only {stats.observation_count} trading days of returns "
                f"in this period. The optimizer needs at least {required}: {self._min_observations_per_stock} "
                f"per stock, and at least {self._min_observations} in total. Choose a longer period."
            )
        optimizer_input = OptimizerInput(
            tickers=stats.tickers,
            expected_returns=stats.annualized_mean_returns,
            covariance=stats.annualized_covariance,
            strategy=selected.name,
            max_weight=max_weight,
            risk_free_rate=risk_free,
            period_start=start_date,
            period_end=end_date,
        )
        expected, covariance = validate_optimizer_input(optimizer_input, self._tolerance)
        weights = selected.compute_weights(
            expected,
            covariance,
            max_weight,
            risk_free,
            target_return=target_return,
            target_volatility=target_volatility,
        )
        expected_return, volatility, sharpe_ratio = _portfolio_metrics(
            weights, expected, covariance, risk_free
        )

        weight_map = {ticker: float(weight) for ticker, weight in zip(stats.tickers, weights)}
        if current_weights is None:
            equal = 1.0 / len(stats.tickers)
            current_list = [equal] * len(stats.tickers)
        else:
            if len(current_weights) != len(stats.tickers):
                raise InvalidOptimizationInputError(
                    "current_weights must have one value for each ticker, in ticker order."
                )
            current_list = [float(value) for value in current_weights]
            if abs(sum(current_list) - 1.0) > self._tolerance:
                raise InvalidOptimizationInputError("current_weights must sum to 1.")
            if any(value < -self._tolerance for value in current_list):
                raise InvalidOptimizationInputError("current_weights cannot be negative.")

        current_return, current_volatility, current_sharpe = _portfolio_metrics(
            np.asarray(current_list, dtype=float), expected, covariance, risk_free
        )
        curve = build_equity_curve(
            batch.histories,
            stats.tickers,
            current_list,
            [weight_map[ticker] for ticker in stats.tickers],
            capital,
        )
        cap = "None" if max_weight is None else f"{max_weight * 100:g}%"
        assumptions = [
            *stats.assumptions,
            f"Price source: {batch.source}; interval {batch.interval}; basis {batch.adjustment_basis}.",
            f"Strategy: {selected.name} (long-only weights sum to 100%).",
            f"Maximum weight per stock: {cap}.",
            *selected.assumptions(target_return=target_return, target_volatility=target_volatility),
            f"Risk-free rate: {risk_free:g} (annual decimal).",
            f"Capital chart starts at {capital:g} with buy-and-hold weights.",
            "Results are historical estimates, not guaranteed outcomes.",
        ]
        return OptimizationResult(
            strategy=selected.name,
            weights=weight_map,
            expected_return=expected_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            current_expected_return=current_return,
            current_volatility=current_volatility,
            current_sharpe_ratio=current_sharpe,
            period_start=start_date,
            period_end=end_date,
            assumptions=assumptions,
            initial_capital=capital,
            equity_curve=[
                EquityCurvePointSchema(
                    date=point.date,
                    current_value=point.current_value,
                    optimized_value=point.optimized_value,
                )
                for point in curve
            ],
        )


def _portfolio_metrics(
    weights: np.ndarray,
    expected: np.ndarray,
    covariance: np.ndarray,
    risk_free: float,
) -> tuple[float, float, float]:
    """Return expected return, volatility, and Sharpe for a weight vector."""
    expected_return = float(weights @ expected)
    volatility = float(np.sqrt(max(float(weights @ covariance @ weights), 0.0)))
    sharpe_ratio = (expected_return - risk_free) / volatility if volatility > 0 else 0.0
    return expected_return, volatility, sharpe_ratio


def create_optimization_service(settings: Settings, session: Session) -> OptimizationService:
    """Build OptimizationService with Settings and an injected DB session."""
    reader = StoredPriceHistoryReader(
        PriceRepository(session),
        required_interval=settings.market_data_interval,
        required_adjustment_basis=settings.market_data_adjustment_basis,
        required_calendar=settings.market_data_calendar,
    )
    tolerance = settings.optimization_tolerance
    solver = settings.optimization_solver
    return OptimizationService(
        reader=reader,
        calendar=WeekdaySessionCalendar(),
        strategies=[
            MinimumVarianceStrategy(tolerance, solver),
            MaxSharpeStrategy(tolerance, solver),
            TargetReturnStrategy(tolerance, solver),
            TargetRiskStrategy(tolerance, solver),
        ],
        annualization_factor=settings.annualization_factor,
        tolerance=tolerance,
        default_risk_free_rate=settings.default_risk_free_rate,
        max_span_days=settings.market_data_max_span_days,
        initial_capital=settings.portfolio_chart_initial_capital,
        min_observations=settings.min_return_observations,
        min_observations_per_stock=settings.min_return_observations_per_stock,
    )
