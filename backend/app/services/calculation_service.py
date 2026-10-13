"""Calculate returns from stored prices without database or provider calls."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from math import isfinite

import numpy as np

from app.core.errors import AppError
from app.market_data.base import PriceBar


@dataclass(frozen=True)
class DailyReturn:
    """One price change between two consecutive trading sessions.

    `value` is a decimal: 0.10 means a 10% gain.
    """

    start_date: date
    end_date: date
    value: float


def calculate_daily_returns(
    prices: Sequence[PriceBar], sessions: Sequence[date]
) -> list[DailyReturn]:
    """Calculate one stock's returns using the expected trading sessions.

    The caller supplies sessions within the selected period, oldest first,
    and confirms that the close prices are adjusted for splits and dividends.
    Price bars can arrive in any order. Both prices for an interval must exist.
    Missing prices are not filled, and missing sessions are not bridged.
    """
    if any(start >= end for start, end in zip(sessions, sessions[1:])):
        raise AppError(
            "Trading sessions must be unique and ordered from oldest to newest.",
            code="invalid_price_history",
            status_code=422,
        )

    expected_dates = set(sessions)
    closes: dict[date, float] = {}
    for bar in prices:
        if bar.date not in expected_dates:
            raise AppError(
                f"Price date {bar.date} is not a trading session in the selected period.",
                code="invalid_price_history",
                status_code=422,
            )
        if bar.date in closes:
            raise AppError(
                f"More than one price was supplied for {bar.date}.",
                code="invalid_price_history",
                status_code=422,
            )
        if not isfinite(bar.close) or bar.close <= 0:
            raise AppError(
                f"The close price for {bar.date} must be finite and greater than zero.",
                code="invalid_price_history",
                status_code=422,
            )
        closes[bar.date] = bar.close

    returns = []
    for start, end in zip(sessions, sessions[1:]):
        if start not in closes or end not in closes:
            continue
        value = closes[end] / closes[start] - 1
        if not isfinite(value):
            raise AppError(
                f"The return from {start} to {end} is not finite.",
                code="invalid_price_history",
                status_code=422,
            )
        returns.append(DailyReturn(start_date=start, end_date=end, value=value))
    return returns


@dataclass(frozen=True)
class ReturnSummary:
    """Returns and averages for the same periods across all selected stocks.

    Rows in `daily_returns` follow `intervals`. Columns and averages follow
    `tickers`. All returns are decimals, and annualization is arithmetic.
    """

    tickers: tuple[str, ...]
    intervals: tuple[tuple[date, date], ...]
    daily_returns: tuple[tuple[float, ...], ...]
    daily_mean_returns: tuple[float, ...]
    annualized_mean_returns: tuple[float, ...]
    annualization_factor: float
    dropped_interval_count: int

    @property
    def observation_count(self) -> int:
        return len(self.intervals)


def calculate_return_summary(
    histories: Mapping[str, Sequence[PriceBar]],
    tickers: Sequence[str],
    sessions: Sequence[date],
    annualization_factor: float,
) -> ReturnSummary:
    """Match daily intervals across stocks and calculate their mean returns.

    The caller supplies normalized tickers and confirms the price basis and
    trading calendar. At least two intervals must exist for every stock.
    `annualization_factor` is the assumed trading sessions per year.
    """
    if not tickers or any(not ticker.strip() for ticker in tickers) or len(set(tickers)) != len(tickers):
        raise AppError(
            "Select at least one stock, with no empty or duplicate tickers.",
            code="invalid_calculation_input",
            status_code=422,
        )
    if not isfinite(annualization_factor) or annualization_factor <= 0:
        raise AppError(
            "The annualization factor must be finite and greater than zero.",
            code="invalid_calculation_input",
            status_code=422,
        )

    returns_by_ticker = {}
    for ticker in tickers:
        if ticker not in histories:
            raise AppError(
                f"No stored price history was supplied for {ticker}.",
                code="insufficient_history",
                status_code=422,
            )
        daily_returns = calculate_daily_returns(histories[ticker], sessions)
        returns_by_ticker[ticker] = {
            (item.start_date, item.end_date): item.value for item in daily_returns
        }

    shared_intervals = set(returns_by_ticker[tickers[0]])
    for ticker in tickers[1:]:
        shared_intervals.intersection_update(returns_by_ticker[ticker])
    intervals = tuple(sorted(shared_intervals))
    if len(intervals) < 2:
        raise AppError(
            "At least two daily return intervals must be available for every selected stock.",
            code="insufficient_history",
            status_code=422,
        )

    values = tuple(
        tuple(returns_by_ticker[ticker][interval] for ticker in tickers)
        for interval in intervals
    )
    with np.errstate(over="ignore", invalid="ignore"):
        means = np.asarray(values, dtype=np.float64).mean(axis=0)
        annualized_means = means * annualization_factor
    if not (np.isfinite(means).all() and np.isfinite(annualized_means).all()):
        raise AppError(
            "The selected prices and annualization factor produce non-finite average returns.",
            code="invalid_calculation_result",
            status_code=422,
        )

    return ReturnSummary(
        tickers=tuple(tickers),
        intervals=intervals,
        daily_returns=values,
        daily_mean_returns=tuple(float(value) for value in means),
        annualized_mean_returns=tuple(float(value) for value in annualized_means),
        annualization_factor=annualization_factor,
        dropped_interval_count=len(sessions) - 1 - len(intervals),
    )


@dataclass(frozen=True)
class CalculationWarning:
    """An explanation for a statistic that cannot be calculated."""

    code: str
    message: str
    tickers: tuple[str, ...]


@dataclass(frozen=True)
class RiskStatistics:
    """Historical risk statistics in the same ticker order as the returns.

    Variance is measured in squared decimal returns. Correlation has no units.
    A `None` correlation means that one of the stocks has zero variance.
    """

    tickers: tuple[str, ...]
    daily_variances: tuple[float, ...]
    annualized_variances: tuple[float, ...]
    daily_covariance: tuple[tuple[float, ...], ...]
    annualized_covariance: tuple[tuple[float, ...], ...]
    correlation: tuple[tuple[float | None, ...], ...]
    warnings: tuple[CalculationWarning, ...]


def calculate_risk_statistics(summary: ReturnSummary) -> RiskStatistics:
    """Calculate sample variance, covariance, and correlation from shared returns.

    Use the return summary from `calculate_return_summary`. Sample covariance
    divides by the number of observations minus one. Annualized covariance
    uses the summary's annualization factor, without scaling correlation.
    """
    count = len(summary.tickers)
    if summary.observation_count < 2:
        raise AppError(
            "At least two shared return intervals are required to calculate risk.",
            code="insufficient_history",
            status_code=422,
        )
    try:
        values = np.asarray(summary.daily_returns, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise AppError(
            "Daily returns must be a numeric row for each shared interval.",
            code="invalid_calculation_input",
            status_code=422,
        ) from error
    if (
        not count
        or values.shape != (summary.observation_count, count)
        or not np.isfinite(values).all()
        or not isfinite(summary.annualization_factor)
        or summary.annualization_factor <= 0
    ):
        raise AppError(
            "Risk calculations require finite returns in ticker order and a positive annualization factor.",
            code="invalid_calculation_input",
            status_code=422,
        )

    with np.errstate(over="ignore", invalid="ignore"):
        covariance = np.atleast_2d(np.cov(values, rowvar=False, ddof=1))
        # Equal observations have zero variance, even if averaging rounds slightly.
        constant = np.all(values == values[0], axis=0)
        covariance[constant, :] = 0
        covariance[:, constant] = 0
        annualized_covariance = covariance * summary.annualization_factor
    if not (np.isfinite(covariance).all() and np.isfinite(annualized_covariance).all()):
        raise AppError(
            "The selected returns produce non-finite risk statistics.",
            code="invalid_calculation_result",
            status_code=422,
        )

    variances = np.diag(covariance)
    standard_deviations = np.sqrt(variances)
    correlation = [[None for _ in range(count)] for _ in range(count)]
    # Allow only rounding at float64 precision, scaled by the matrix dimensions.
    rounding_tolerance = np.finfo(np.float64).eps * max(values.shape)
    for row in range(count):
        for column in range(row, count):
            if variances[row] == 0 or variances[column] == 0:
                continue
            value = covariance[row, column] / standard_deviations[row] / standard_deviations[column]
            if not isfinite(value) or abs(value) > 1 + rounding_tolerance:
                raise AppError(
                    "The selected returns produce an invalid correlation.",
                    code="invalid_calculation_result",
                    status_code=422,
                )
            value = 1.0 if row == column else float(np.clip(value, -1, 1))
            correlation[row][column] = value
            correlation[column][row] = value

    warnings = tuple(
        CalculationWarning(
            code="undefined_correlation",
            message=f"Correlation is undefined for {ticker} because its return variance is zero.",
            tickers=(ticker,),
        )
        for ticker, variance in zip(summary.tickers, variances)
        if variance == 0
    )
    return RiskStatistics(
        tickers=summary.tickers,
        daily_variances=tuple(float(value) for value in variances),
        annualized_variances=tuple(float(value) for value in np.diag(annualized_covariance)),
        daily_covariance=tuple(tuple(float(value) for value in row) for row in covariance),
        annualized_covariance=tuple(tuple(float(value) for value in row) for row in annualized_covariance),
        correlation=tuple(tuple(row) for row in correlation),
        warnings=warnings,
    )
