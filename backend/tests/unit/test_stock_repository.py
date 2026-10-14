"""Unit tests for StockRepository upsert."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.market_data.base import StockInfo
from app.models.stock import Stock
from app.repositories.stock_repository import StockRepository


@pytest.fixture
def session() -> Session:
    # Import price history so metadata matches the app models; only stocks are used here.
    import app.models.price_history  # noqa: F401

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()


def test_upsert_inserts_a_new_stock(session: Session):
    repo = StockRepository(session)
    info = StockInfo(
        symbol="AAPL",
        name="Apple Inc.",
        currency="USD",
        exchange="NMS",
        quote_type="EQUITY",
    )

    row = repo.upsert(info)

    assert row.symbol == "AAPL"
    assert row.name == "Apple Inc."
    assert row.currency == "USD"
    assert row.exchange == "NMS"
    assert session.get(Stock, "AAPL") is row


def test_upsert_updates_an_existing_stock_without_duplicates(session: Session):
    repo = StockRepository(session)
    repo.upsert(
        StockInfo(symbol="AAPL", name="Apple", currency="USD", exchange="NMS", quote_type="EQUITY")
    )

    second = repo.upsert(
        StockInfo(
            symbol="AAPL",
            name="Apple Inc.",
            currency="USD",
            exchange="XNAS",
            quote_type="EQUITY",
        )
    )

    rows = session.scalars(select(Stock)).all()
    assert len(rows) == 1
    assert second.name == "Apple Inc."
    assert second.exchange == "XNAS"
