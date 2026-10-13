"""Read saved price histories, check their basis, and calculate statistics."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from typing import Protocol

from app.core.errors import AppError
from app.market_data.base import PriceBar
from app.services.calculation_service import (
    CalculationWarning,
    ReturnSummary,
    RiskStatistics,
    calculate_return_summary,
    calculate_risk_statistics,
)


@dataclass(frozen=True)
class PriceHistoryMetadata:
    """Facts saved when the prices were collected; unknown facts remain None."""

    source: str | None
    retrieved_at: datetime | None
    adjustment_basis: str | None
    interval: str | None
    exchange: str | None
    calendar: str | None


@dataclass(frozen=True)
class StoredPriceHistory:
    prices: tuple[PriceBar, ...]
    metadata: PriceHistoryMetadata | None


PriceHistoryBatch = Mapping[str, StoredPriceHistory]


class PriceHistoryReader(Protocol):
    """Read one batch from storage without contacting the market-data provider.

    Keys are normalized tickers. Missing histories can be omitted. Storage
    failures must raise AppError with code price_history_unavailable and 503.
    """

    def read_adjusted_history(
        self, tickers: Sequence[str], start_date: date, end_date: date
    ) -> PriceHistoryBatch: ...


class SessionCalendar(Protocol):
    """Supply all exchange trading dates within the requested inclusive period."""

    name: str

    def sessions_in_range(self, start_date: date, end_date: date) -> Sequence[date]: ...


@dataclass(frozen=True)
class CalculationResult:
    period_start: date
    period_end: date
    calendar: str
    returns: ReturnSummary
    risk: RiskStatistics
    source_metadata: Mapping[str, PriceHistoryMetadata]
    warnings: tuple[CalculationWarning, ...]


class StoredCalculationService:
    """Connect saved prices to the pure calculation functions.

    The caller supplies the reader, calendar, and configured yearly factor.
    No database schema or provider implementation is assumed here.
    """

    def __init__(
        self, reader: PriceHistoryReader, calendar: SessionCalendar, annualization_factor: float
    ) -> None:
        if not isfinite(annualization_factor) or annualization_factor <= 0:
            raise AppError(
                "The annualization factor must be positive and finite.",
                code="invalid_calculation_input", status_code=422,
            )
        self._reader = reader
        self._calendar = calendar
        self._annualization_factor = annualization_factor

    def calculate(self, tickers: Sequence[str], start_date: date, end_date: date) -> CalculationResult:
        selected = tuple(ticker.strip().upper() for ticker in tickers)
        if not selected or any(not ticker for ticker in selected) or len(set(selected)) != len(selected):
            raise AppError(
                "Select stocks with no empty or duplicate tickers.",
                code="invalid_calculation_input", status_code=422,
            )
        if start_date >= end_date:
            raise AppError(
                "The start date must be before the end date.",
                code="invalid_calculation_input", status_code=422,
            )

        sessions = tuple(self._calendar.sessions_in_range(start_date, end_date))
        if (
            any(day < start_date or day > end_date for day in sessions)
            or any(start >= end for start, end in zip(sessions, sessions[1:]))
        ):
            raise AppError(
                "The calendar must return ordered, unique trading dates within the period.",
                code="invalid_price_history", status_code=422,
            )
        if len(sessions) < 3:
            raise AppError(
                "The selected period needs at least three trading sessions.",
                code="insufficient_history", status_code=422,
            )

        batch = self._reader.read_adjusted_history(selected, start_date, end_date)
        histories = {}
        metadata = {}
        for ticker in selected:
            history = batch.get(ticker)
            if history is None:
                raise AppError(
                    f"No stored price history is available for {ticker}.",
                    code="insufficient_history", status_code=422,
                )
            metadata[ticker] = self._check_metadata(ticker, history.metadata)
            histories[ticker] = history.prices

        returns = calculate_return_summary(histories, selected, sessions, self._annualization_factor)
        risk = calculate_risk_statistics(returns)
        warnings = risk.warnings
        if returns.dropped_interval_count:
            warnings += (CalculationWarning(
                code="dropped_intervals",
                message=f"Dropped {returns.dropped_interval_count} return intervals with missing prices.",
                tickers=selected,
            ),)
        return CalculationResult(
            period_start=start_date, period_end=end_date, calendar=self._calendar.name,
            returns=returns, risk=risk, source_metadata=metadata, warnings=warnings,
        )

    def _check_metadata(
        self, ticker: str, metadata: PriceHistoryMetadata | None
    ) -> PriceHistoryMetadata:
        if (
            metadata is None
            or not metadata.source or not metadata.source.strip()
            or not metadata.exchange or not metadata.exchange.strip()
            or metadata.retrieved_at is None or metadata.retrieved_at.utcoffset() is None
            or metadata.adjustment_basis != "split_dividend_adjusted"
            or metadata.interval != "1d"
            or not metadata.calendar or metadata.calendar != self._calendar.name
        ):
            raise AppError(
                f"Stored prices for {ticker} need source, exchange, and timezone-aware retrieval time, "
                "plus daily split/dividend-adjusted prices on the selected calendar.",
                code="invalid_price_history", status_code=422,
            )
        return metadata
