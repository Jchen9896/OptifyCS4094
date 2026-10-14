"""PostgreSQL integration for price history upsert and DB-first reuse."""

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.market_data.base import MarketDataProvider, PriceBar, StockInfo
from app.models.price_history import PriceBarRow
from app.repositories.price_repository import PriceRepository
from app.repositories.stock_repository import StockRepository
from app.services.market_data_service import MarketDataService
from app.services.stock_service import StockService

SYMBOL = "TSTPG1"


class FakeProvider(MarketDataProvider):
    def __init__(self, bars: list[PriceBar]):
        self.bars = bars
        self.history_calls = 0

    def get_stock(self, symbol: str) -> StockInfo:
        return StockInfo(
            symbol=symbol,
            name="Postgres Test Stock",
            currency="USD",
            exchange="NMS",
            quote_type="EQUITY",
        )

    def get_price_history(self, symbol: str, start: date, end: date) -> list[PriceBar]:
        self.history_calls += 1
        return list(self.bars)

    def search_stocks(self, query: str) -> list[StockInfo]:
        return []


@pytest.fixture
def pg_session() -> Session:
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    try:
        connection = engine.connect()
        connection.rollback()
    except Exception as error:
        pytest.skip(f"PostgreSQL is not available: {error}")

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def _service(session: Session, provider: FakeProvider) -> MarketDataService:
    return MarketDataService(
        provider=provider,
        stock_service=StockService(provider, get_settings().ticker_pattern, ["EQUITY", "ETF"]),
        stock_repository=StockRepository(session),
        price_repository=PriceRepository(session),
        max_span_days=get_settings().market_data_max_span_days,
        source=get_settings().market_data_source,
        interval=get_settings().market_data_interval,
        adjustment_basis=get_settings().market_data_adjustment_basis,
        calendar=get_settings().market_data_calendar,
    )


def test_postgres_upsert_is_idempotent_and_serves_from_database(pg_session: Session):
    bars = [
        PriceBar(date=date(2026, 1, 2), open=1.0, high=2.0, low=0.5, close=1.5, volume=100),
        PriceBar(date=date(2026, 1, 5), open=1.5, high=2.5, low=1.0, close=2.0, volume=200),
    ]
    provider = FakeProvider(bars)
    service = _service(pg_session, provider)

    first = service.get_or_fetch_history(SYMBOL, date(2026, 1, 2), date(2026, 1, 5))
    second = service.get_or_fetch_history(SYMBOL, date(2026, 1, 2), date(2026, 1, 5))

    rows = pg_session.scalars(
        select(PriceBarRow).where(PriceBarRow.symbol == SYMBOL).order_by(PriceBarRow.date)
    ).all()

    assert first.served_from_database is False
    assert second.served_from_database is True
    assert provider.history_calls == 1
    assert len(rows) == 2
    assert second.bar_count == 2
    assert PriceRepository(pg_session).list_range(SYMBOL, date(2026, 1, 2), date(2026, 1, 5)) == list(rows)
