"""Unit tests for MarketDataService database-first history."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.core.errors import InsufficientHistoryError, InvalidDateRangeError, TickerNotFoundError
from app.market_data.base import MarketDataProvider, PriceBar, StockInfo
from app.repositories.price_repository import PriceRepository
from app.repositories.stock_repository import StockRepository
from app.services.market_data_service import MarketDataService
from app.services.stock_service import StockService


class FakeProvider(MarketDataProvider):
    def __init__(self, stock: StockInfo | None = None, bars: list[PriceBar] | None = None):
        self.stock = stock
        self.bars = bars or []
        self.history_calls = 0
        self.stock_calls = 0

    def get_stock(self, symbol: str) -> StockInfo:
        self.stock_calls += 1
        if self.stock is None:
            raise TickerNotFoundError(symbol)
        return self.stock

    def get_price_history(self, symbol: str, start: date, end: date) -> list[PriceBar]:
        self.history_calls += 1
        return list(self.bars)

    def search_stocks(self, query: str) -> list[StockInfo]:
        return []


@pytest.fixture
def session() -> Session:
    import app.models.price_history  # noqa: F401
    import app.models.stock  # noqa: F401

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()


def _service(session: Session, provider: FakeProvider) -> MarketDataService:
    stock_service = StockService(provider, r"[A-Z0-9.\-^=]{1,15}", ["EQUITY", "ETF"])
    return MarketDataService(
        provider=provider,
        stock_service=stock_service,
        stock_repository=StockRepository(session),
        price_repository=PriceRepository(session),
        max_span_days=3650,
        source="yfinance",
        interval="1d",
        adjustment_basis="split_dividend_adjusted",
        calendar="XNYS",
    )


def _apple() -> StockInfo:
    return StockInfo(symbol="AAPL", name="Apple Inc.", currency="USD", exchange="NMS", quote_type="EQUITY")


def _bars() -> list[PriceBar]:
    return [
        PriceBar(date=date(2026, 1, 2), open=1.0, high=2.0, low=0.5, close=1.5, volume=100),
        PriceBar(date=date(2026, 1, 5), open=1.5, high=2.5, low=1.0, close=2.0, volume=200),
    ]


def test_get_or_fetch_history_fetches_and_stores(session: Session):
    provider = FakeProvider(stock=_apple(), bars=_bars())
    result = _service(session, provider).get_or_fetch_history("aapl", date(2026, 1, 2), date(2026, 1, 5))

    assert provider.history_calls == 1
    assert result.served_from_database is False
    assert result.bar_count == 2
    assert result.symbol == "AAPL"
    assert result.source == "yfinance"
    stored = PriceRepository(session).list_range("AAPL", date(2026, 1, 2), date(2026, 1, 5))
    assert len(stored) == 2
    assert stored[0].close == Decimal("1.5")


def test_get_or_fetch_history_uses_database_on_second_call(session: Session):
    provider = FakeProvider(stock=_apple(), bars=_bars())
    service = _service(session, provider)
    service.get_or_fetch_history("AAPL", date(2026, 1, 2), date(2026, 1, 5))

    result = service.get_or_fetch_history("AAPL", date(2026, 1, 2), date(2026, 1, 5))

    assert provider.history_calls == 1
    assert provider.stock_calls == 1
    assert result.served_from_database is True
    assert result.bar_count == 2


def test_get_or_fetch_history_rejects_invalid_range(session: Session):
    provider = FakeProvider(stock=_apple(), bars=_bars())
    with pytest.raises(InvalidDateRangeError):
        _service(session, provider).get_or_fetch_history("AAPL", date(2026, 1, 5), date(2026, 1, 2))
    assert provider.history_calls == 0


def test_get_or_fetch_history_rejects_empty_provider_bars(session: Session):
    provider = FakeProvider(stock=_apple(), bars=[])
    with pytest.raises(InsufficientHistoryError):
        _service(session, provider).get_or_fetch_history("AAPL", date(2026, 1, 2), date(2026, 1, 5))


def test_get_or_fetch_history_passes_through_ticker_errors(session: Session):
    provider = FakeProvider(stock=None, bars=_bars())
    with pytest.raises(TickerNotFoundError):
        _service(session, provider).get_or_fetch_history("ZZZZ", date(2026, 1, 2), date(2026, 1, 5))
