"""Calculate returns from stored prices without database or provider calls."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from math import isfinite

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
