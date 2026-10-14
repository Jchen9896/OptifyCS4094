"""Unit tests for PriceRepository upsert and range read."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.market_data.base import PriceBar, StockInfo
from app.models.price_history import PriceBarRow
from app.repositories.price_repository import PriceRepository
from app.repositories.stock_repository import StockRepository


PROVENANCE = {
    "source": "yfinance",
    "interval": "1d",
    "adjustment_basis": "split_dividend_adjusted",
    "calendar": "XNYS",
}


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


def _seed_stock(session: Session, symbol: str = "AAPL") -> None:
    StockRepository(session).upsert(
        StockInfo(symbol=symbol, name="Apple Inc.", currency="USD", exchange="NMS", quote_type="EQUITY")
    )


def test_upsert_bars_inserts_rows(session: Session):
    _seed_stock(session)
    repo = PriceRepository(session)
    fetched_at = datetime(2026, 10, 14, tzinfo=timezone.utc)
    bars = [
        PriceBar(date=date(2026, 1, 2), open=1.0, high=2.0, low=0.5, close=1.5, volume=100),
        PriceBar(date=date(2026, 1, 3), open=1.5, high=2.5, low=1.0, close=2.0, volume=200),
    ]

    rows = repo.upsert_bars("AAPL", bars, fetched_at=fetched_at, **PROVENANCE)

    assert len(rows) == 2
    assert rows[0].close == Decimal("1.5")
    assert rows[0].source == "yfinance"
    assert rows[1].date == date(2026, 1, 3)


def test_upsert_bars_updates_same_symbol_date_without_duplicates(session: Session):
    _seed_stock(session)
    repo = PriceRepository(session)
    first_fetched = datetime(2026, 10, 1, tzinfo=timezone.utc)
    second_fetched = datetime(2026, 10, 14, tzinfo=timezone.utc)
    bar = PriceBar(date=date(2026, 1, 2), open=1.0, high=2.0, low=0.5, close=1.5, volume=100)

    repo.upsert_bars("AAPL", [bar], fetched_at=first_fetched, **PROVENANCE)
    updated = PriceBar(date=date(2026, 1, 2), open=1.1, high=2.1, low=0.6, close=1.8, volume=150)
    repo.upsert_bars("AAPL", [updated], fetched_at=second_fetched, **PROVENANCE)

    rows = session.scalars(select(PriceBarRow)).all()
    assert len(rows) == 1
    assert rows[0].close == Decimal("1.8")
    assert rows[0].volume == 150
    # SQLite may drop tzinfo; compare the calendar instant only.
    assert rows[0].fetched_at.replace(tzinfo=timezone.utc) == second_fetched


def test_list_range_returns_inclusive_ordered_bars(session: Session):
    _seed_stock(session)
    repo = PriceRepository(session)
    fetched_at = datetime(2026, 10, 14, tzinfo=timezone.utc)
    repo.upsert_bars(
        "AAPL",
        [
            PriceBar(date=date(2026, 1, 1), open=1.0, high=1.0, low=1.0, close=1.0, volume=1),
            PriceBar(date=date(2026, 1, 2), open=2.0, high=2.0, low=2.0, close=2.0, volume=2),
            PriceBar(date=date(2026, 1, 3), open=3.0, high=3.0, low=3.0, close=3.0, volume=3),
            PriceBar(date=date(2026, 1, 4), open=4.0, high=4.0, low=4.0, close=4.0, volume=4),
        ],
        fetched_at=fetched_at,
        **PROVENANCE,
    )

    rows = repo.list_range("AAPL", date(2026, 1, 2), date(2026, 1, 3))

    assert [row.date for row in rows] == [date(2026, 1, 2), date(2026, 1, 3)]
    assert rows[0].close == Decimal("2.0")


def test_list_range_returns_empty_when_no_rows(session: Session):
    _seed_stock(session)
    assert PriceRepository(session).list_range("AAPL", date(2026, 1, 1), date(2026, 1, 31)) == []
