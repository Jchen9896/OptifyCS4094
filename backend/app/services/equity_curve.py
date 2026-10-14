"""Build portfolio capital paths from aligned closes and fixed weights."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.core.errors import InvalidCalculationInputError, InsufficientHistoryError
from app.market_data.base import PriceBar


@dataclass(frozen=True)
class EquityCurvePoint:
    """Portfolio capital on one shared trading date."""

    date: date
    current_value: float
    optimized_value: float


def build_equity_curve(
    histories: dict[str, list[PriceBar]],
    tickers: list[str],
    current_weights: list[float],
    optimized_weights: list[float],
    initial_capital: float,
) -> list[EquityCurvePoint]:
    """Return capital over time for current and optimized weights.

    Each path starts at `initial_capital` on the first shared date and uses
    buy-and-hold weights: value_t = initial * sum_i w_i * (price_i,t / price_i,0).
    """
    if initial_capital <= 0:
        raise InvalidCalculationInputError("Initial capital must be a positive number.")
    if len(tickers) != len(current_weights) or len(tickers) != len(optimized_weights):
        raise InvalidCalculationInputError("Weight vectors must match the ticker list.")

    price_maps = {ticker: {bar.date: float(bar.close) for bar in histories[ticker]} for ticker in tickers}
    shared_dates = sorted(set.intersection(*(set(price_maps[ticker]) for ticker in tickers)))
    if len(shared_dates) < 2:
        raise InsufficientHistoryError(
            "There are not enough shared prices to build a capital path for the chart."
        )

    base = {ticker: price_maps[ticker][shared_dates[0]] for ticker in tickers}
    points: list[EquityCurvePoint] = []
    for day in shared_dates:
        current = 0.0
        optimized = 0.0
        for index, ticker in enumerate(tickers):
            relative = price_maps[ticker][day] / base[ticker]
            current += current_weights[index] * relative
            optimized += optimized_weights[index] * relative
        points.append(
            EquityCurvePoint(
                date=day,
                current_value=initial_capital * current,
                optimized_value=initial_capital * optimized,
            )
        )
    return points
