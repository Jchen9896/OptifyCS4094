"""Fetch and store historical prices with database-first reuse (Decision 006)."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.market_data.base import MarketDataProvider, PriceBar
from app.market_data.yfinance_provider import create_yfinance_provider
from app.repositories.price_repository import PriceRepository
from app.repositories.stock_repository import StockRepository
from app.services.history_validation import validate_date_range, validate_price_bars
from app.services.stock_service import StockService


@dataclass(frozen=True)
class PriceHistoryResult:
    """Stored history returned to the API layer."""

    symbol: str
    start_date: date
    end_date: date
    bar_count: int
    first_date: date | None
    last_date: date | None
    last_close: float | None
    source: str
    fetched_at: datetime | None
    served_from_database: bool


class MarketDataService:
    """Read stored bars first; call the provider only when the range is not covered."""

    def __init__(
        self,
        provider: MarketDataProvider,
        stock_service: StockService,
        stock_repository: StockRepository,
        price_repository: PriceRepository,
        *,
        max_span_days: int,
        source: str,
        interval: str,
        adjustment_basis: str,
        calendar: str,
    ) -> None:
        self._provider = provider
        self._stock_service = stock_service
        self._stock_repository = stock_repository
        self._price_repository = price_repository
        self._max_span_days = max_span_days
        self._source = source
        self._interval = interval
        self._adjustment_basis = adjustment_basis
        self._calendar = calendar

    def get_or_fetch_history(self, symbol: str, start: date, end: date) -> PriceHistoryResult:
        """Return daily history for one symbol. Prefer price_bars; fetch only on gaps."""
        validate_date_range(start, end, self._max_span_days)
        normalized = symbol.strip().upper()
        stored = self._price_repository.list_range(normalized, start, end)
        if self._range_is_covered(stored, start, end):
            return self._to_result(normalized, start, end, stored, served_from_database=True)

        stock = self._stock_service.validate_ticker(normalized)
        bars = self._provider.get_price_history(normalized, start, end)
        validate_price_bars(bars)
        fetched_at = datetime.now(timezone.utc)
        self._stock_repository.upsert(stock)
        self._price_repository.upsert_bars(
            normalized,
            bars,
            fetched_at=fetched_at,
            source=self._source,
            interval=self._interval,
            adjustment_basis=self._adjustment_basis,
            calendar=self._calendar,
        )
        stored = self._price_repository.list_range(normalized, start, end)
        return self._to_result(normalized, start, end, stored, served_from_database=False)

    @staticmethod
    def _range_is_covered(rows: list, start: date, end: date) -> bool:
        # Without an exchange calendar, treat endpoint dates as the coverage bounds.
        # Holiday-aware coverage is deferred (Decision 006).
        return bool(rows) and rows[0].date <= start and rows[-1].date >= end

    def _to_result(
        self,
        symbol: str,
        start: date,
        end: date,
        rows: list,
        *,
        served_from_database: bool,
    ) -> PriceHistoryResult:
        return PriceHistoryResult(
            symbol=symbol,
            start_date=start,
            end_date=end,
            bar_count=len(rows),
            first_date=rows[0].date if rows else None,
            last_date=rows[-1].date if rows else None,
            last_close=float(rows[-1].close) if rows else None,
            source=rows[0].source if rows else self._source,
            fetched_at=rows[0].fetched_at if rows else None,
            served_from_database=served_from_database,
        )


def create_market_data_service(settings: Settings, session: Session) -> MarketDataService:
    """Make a MarketDataService with Settings and an injected DB session."""
    provider = create_yfinance_provider(settings)
    stock_service = StockService(
        provider=provider,
        ticker_pattern=settings.ticker_pattern,
        supported_types=settings.supported_security_type_list,
    )
    return MarketDataService(
        provider=provider,
        stock_service=stock_service,
        stock_repository=StockRepository(session),
        price_repository=PriceRepository(session),
        max_span_days=settings.market_data_max_span_days,
        source=settings.market_data_source,
        interval=settings.market_data_interval,
        adjustment_basis=settings.market_data_adjustment_basis,
        calendar=settings.market_data_calendar,
    )
