"""Pure return, mean, and covariance calculations (Decision 005)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite

import numpy as np

from app.core.errors import (
    InsufficientHistoryError,
    InvalidCalculationInputError,
    InvalidCalculationResultError,
    InvalidPriceHistoryError,
)
from app.market_data.base import PriceBar


@dataclass(frozen=True)
class DailyReturn:
    """Simple return between two consecutive expected sessions."""

    start_date: date
    end_date: date
    value: float


@dataclass(frozen=True)
class PortfolioStatistics:
    """Aligned return statistics ready for the optimizer."""

    tickers: list[str]
    annualized_mean_returns: list[float]
    annualized_covariance: list[list[float]]
    observation_count: int
    dropped_interval_count: int
    assumptions: list[str]


def calculate_daily_returns(prices: list[PriceBar], sessions: list[date]) -> list[DailyReturn]:
    """Build simple returns for consecutive sessions. Skip pairs with a missing price."""
    by_date = _price_map(prices)
    returns: list[DailyReturn] = []
    for start, end in zip(sessions, sessions[1:]):
        left = by_date.get(start)
        right = by_date.get(end)
        if left is None or right is None:
            continue
        value = right / left - 1.0
        if not isfinite(value):
            raise InvalidPriceHistoryError(
                f"The return from {start} to {end} is not a finite number."
            )
        returns.append(DailyReturn(start_date=start, end_date=end, value=value))
    return returns


def calculate_portfolio_statistics(
    histories: dict[str, list[PriceBar]],
    tickers: list[str],
    sessions: list[date],
    annualization_factor: float,
) -> PortfolioStatistics:
    """Align returns across tickers and compute annualized means and covariance."""
    _validate_tickers(tickers)
    if annualization_factor <= 0 or not isfinite(annualization_factor):
        raise InvalidCalculationInputError("The annualization factor must be a positive finite number.")
    if len(sessions) < 2:
        raise InsufficientHistoryError("Choose a longer date range so each stock has enough prices.")

    per_ticker = {ticker: {item.start_date: item.value for item in calculate_daily_returns(histories[ticker], sessions)} for ticker in tickers}
    possible = list(zip(sessions, sessions[1:]))
    aligned_starts = [
        start
        for start, _end in possible
        if all(start in per_ticker[ticker] for ticker in tickers)
    ]
    if len(aligned_starts) < 2:
        raise InsufficientHistoryError(
            "There are not enough shared trading days across the selected stocks for this range."
        )

    matrix = np.asarray(
        [[per_ticker[ticker][start] for ticker in tickers] for start in aligned_starts],
        dtype=float,
    )
    if not np.isfinite(matrix).all():
        raise InvalidCalculationResultError("The aligned returns contain missing or infinite values.")

    daily_means = matrix.mean(axis=0)
    # Sample covariance (ddof=1) matches the calculation spec.
    daily_cov = np.cov(matrix, rowvar=False, ddof=1)
    if daily_cov.ndim == 0:
        daily_cov = np.asarray([[float(daily_cov)]])

    annual_means = daily_means * annualization_factor
    annual_cov = daily_cov * annualization_factor
    if not (np.isfinite(annual_means).all() and np.isfinite(annual_cov).all()):
        raise InvalidCalculationResultError("The annualized statistics are not finite.")

    return PortfolioStatistics(
        tickers=list(tickers),
        annualized_mean_returns=annual_means.tolist(),
        annualized_covariance=annual_cov.tolist(),
        observation_count=len(aligned_starts),
        dropped_interval_count=len(possible) - len(aligned_starts),
        assumptions=[
            "Prices use the stored adjusted daily close.",
            "Daily returns use the simple formula r = price_t / price_t-1 - 1.",
            f"Means and covariance are annualized with factor {annualization_factor:g}.",
            "Sample covariance uses denominator n - 1.",
        ],
    )


def _validate_tickers(tickers: list[str]) -> None:
    if not tickers:
        raise InvalidCalculationInputError("Select at least one ticker for calculation.")
    if len(tickers) != len(set(tickers)):
        raise InvalidCalculationInputError("Each ticker may appear only once.")


def _price_map(prices: list[PriceBar]) -> dict[date, float]:
    by_date: dict[date, float] = {}
    for bar in prices:
        if bar.date in by_date:
            raise InvalidPriceHistoryError(f"The price history has a duplicate date ({bar.date}).")
        if not isfinite(bar.close) or bar.close <= 0:
            raise InvalidPriceHistoryError(f"The price history has an invalid close on {bar.date}.")
        by_date[bar.date] = float(bar.close)
    return by_date
