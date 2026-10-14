"""Assemble stored-history statistics and run an optimization strategy."""

from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import InvalidCalculationInputError, InvalidOptimizationInputError
from app.optimization.base import OptimizationStrategy
from app.optimization.mean_variance import MinimumVarianceStrategy
from app.optimization.validation import validate_optimizer_input
from app.repositories.price_repository import PriceRepository
from app.schemas.optimization import OptimizationResult, OptimizerInput
from app.services.calculation_service import calculate_portfolio_statistics
from app.services.history_validation import validate_date_range
from app.services.price_history_reader import StoredPriceHistoryReader
from app.services.session_calendar import SessionCalendar, WeekdaySessionCalendar


STRATEGY_ALIASES = {
    "min_variance": "min_variance",
    "minvar": "min_variance",
    # Demo MVP: mean-variance UI selection runs minimum variance until Sharpe MVO lands.
    "mvo": "min_variance",
}


class OptimizationService:
    """Read stored prices, calculate statistics, and return allocation weights."""

    def __init__(
        self,
        reader: StoredPriceHistoryReader,
        calendar: SessionCalendar,
        strategies: dict[str, OptimizationStrategy],
        *,
        annualization_factor: float,
        tolerance: float,
        default_risk_free_rate: float,
        max_span_days: int,
    ) -> None:
        self._reader = reader
        self._calendar = calendar
        self._strategies = strategies
        self._annualization_factor = annualization_factor
        self._tolerance = tolerance
        self._default_risk_free_rate = default_risk_free_rate
        self._max_span_days = max_span_days

    def run(
        self,
        tickers: list[str],
        start_date,
        end_date,
        *,
        strategy: str,
        max_weight: float | None,
        risk_free_rate: float | None,
    ) -> OptimizationResult:
        """Optimize weights for `tickers` over the stored history in the date range."""
        validate_date_range(start_date, end_date, self._max_span_days)
        normalized = [ticker.strip().upper() for ticker in tickers]
        if len(normalized) < 2:
            raise InvalidOptimizationInputError("Select at least two tickers for optimization.")
        if len(normalized) != len(set(normalized)):
            raise InvalidOptimizationInputError("Each ticker may appear only once.")

        strategy_name = STRATEGY_ALIASES.get(strategy.strip().lower())
        if strategy_name is None or strategy_name not in self._strategies:
            raise InvalidCalculationInputError(
                f"Strategy '{strategy}' is not supported. Use min_variance."
            )
        risk_free = (
            self._default_risk_free_rate if risk_free_rate is None else risk_free_rate
        )

        batch = self._reader.read_adjusted_history(normalized, start_date, end_date)
        sessions = self._calendar.sessions_in_range(start_date, end_date)
        stats = calculate_portfolio_statistics(
            batch.histories,
            normalized,
            sessions,
            self._annualization_factor,
        )
        optimizer_input = OptimizerInput(
            tickers=stats.tickers,
            expected_returns=stats.annualized_mean_returns,
            covariance=stats.annualized_covariance,
            strategy=strategy_name,
            max_weight=max_weight,
            risk_free_rate=risk_free,
            period_start=start_date,
            period_end=end_date,
        )
        expected, covariance = validate_optimizer_input(optimizer_input, self._tolerance)
        weights = self._strategies[strategy_name].compute_weights(
            expected, covariance, max_weight, risk_free
        )
        expected_return = float(weights @ expected)
        variance = float(weights @ covariance @ weights)
        volatility = float(np.sqrt(max(variance, 0.0)))
        sharpe_ratio = (expected_return - risk_free) / volatility if volatility > 0 else 0.0

        assumptions = [
            *stats.assumptions,
            f"Price source: {batch.source}; interval {batch.interval}; basis {batch.adjustment_basis}.",
            f"Strategy: {strategy_name} (long-only weights sum to 100%).",
            f"Risk-free rate: {risk_free:g} (annual decimal).",
            "Results are historical estimates, not guaranteed outcomes.",
        ]
        return OptimizationResult(
            strategy=strategy_name,
            weights={ticker: float(weight) for ticker, weight in zip(stats.tickers, weights)},
            expected_return=expected_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            period_start=start_date,
            period_end=end_date,
            assumptions=assumptions,
        )


def create_optimization_service(settings: Settings, session: Session) -> OptimizationService:
    """Build OptimizationService with Settings and an injected DB session."""
    reader = StoredPriceHistoryReader(
        PriceRepository(session),
        required_interval=settings.market_data_interval,
        required_adjustment_basis=settings.market_data_adjustment_basis,
        required_calendar=settings.market_data_calendar,
    )
    tolerance = settings.optimization_tolerance
    return OptimizationService(
        reader=reader,
        calendar=WeekdaySessionCalendar(),
        strategies={"min_variance": MinimumVarianceStrategy(tolerance)},
        annualization_factor=settings.annualization_factor,
        tolerance=tolerance,
        default_risk_free_rate=settings.default_risk_free_rate,
        max_span_days=settings.market_data_max_span_days,
    )
