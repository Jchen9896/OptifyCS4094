"""Pure checks for history date ranges and price bar quality (M07, M10)."""

import math
from datetime import date

from app.core.errors import InsufficientHistoryError, InvalidDateRangeError, UnreliablePriceHistoryError
from app.market_data.base import PriceBar


def validate_date_range(start: date, end: date, max_span_days: int) -> None:
    """Reject missing, reversed, equal, or over-long date ranges."""
    if start >= end:
        raise InvalidDateRangeError("Choose a start date that is before the end date.")
    span_days = (end - start).days
    if span_days > max_span_days:
        raise InvalidDateRangeError(
            f"The date range must be at most {max_span_days} days. Choose a shorter range."
        )


def validate_price_bars(bars: list[PriceBar]) -> None:
    """Reject empty, duplicate, or invalid OHLCV rows before storage."""
    if not bars:
        raise InsufficientHistoryError()

    seen_dates: set[date] = set()
    for bar in bars:
        if bar.date in seen_dates:
            raise UnreliablePriceHistoryError(
                f"The price history has a duplicate date ({bar.date}). Choose another range or symbol."
            )
        seen_dates.add(bar.date)

        values = (bar.open, bar.high, bar.low, bar.close)
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise UnreliablePriceHistoryError(
                f"The price history has an invalid price on {bar.date}. Choose another range or symbol."
            )
        if bar.high < bar.low:
            raise UnreliablePriceHistoryError(
                f"The price history has high below low on {bar.date}. Choose another range or symbol."
            )
        if not math.isfinite(bar.volume) or bar.volume < 0:
            raise UnreliablePriceHistoryError(
                f"The price history has an invalid volume on {bar.date}. Choose another range or symbol."
            )
