"""Unit tests for stored price reading and weekday session lists."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.core.errors import InsufficientHistoryError, InvalidPriceHistoryError
from app.market_data.base import PriceBar, StockInfo
from app.repositories.price_repository import PriceRepository
from app.repositories.stock_repository import StockRepository
from app.services.price_history_reader import StoredPriceHistoryReader
from app.services.session_calendar import WeekdaySessionCalendar


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


def _seed(session: Session, symbol: str = "AAPL") -> PriceRepository:
    StockRepository(session).upsert(
        StockInfo(symbol=symbol, name=symbol, currency="USD", exchange="NMS", quote_type="EQUITY")
    )
    return PriceRepository(session)


def test_weekday_session_calendar_skips_weekend():
    sessions = WeekdaySessionCalendar().sessions_in_range(date(2026, 9, 4), date(2026, 9, 7))
    assert sessions == [date(2026, 9, 4), date(2026, 9, 7)]


def test_reader_returns_stored_bars(session: Session):
    repo = _seed(session)
    repo.upsert_bars(
        "AAPL",
        [PriceBar(date=date(2026, 1, 2), open=1, high=2, low=0.5, close=1.5, volume=10)],
        fetched_at=datetime(2026, 10, 14, tzinfo=timezone.utc),
        **PROVENANCE,
    )
    reader = StoredPriceHistoryReader(
        repo,
        required_interval="1d",
        required_adjustment_basis="split_dividend_adjusted",
        required_calendar="XNYS",
    )

    batch = reader.read_adjusted_history(["AAPL"], date(2026, 1, 1), date(2026, 1, 31))

    assert batch.histories["AAPL"][0].close == 1.5
    assert batch.adjustment_basis == "split_dividend_adjusted"


def test_reader_rejects_empty_history(session: Session):
    repo = _seed(session)
    reader = StoredPriceHistoryReader(
        repo,
        required_interval="1d",
        required_adjustment_basis="split_dividend_adjusted",
        required_calendar="XNYS",
    )
    with pytest.raises(InsufficientHistoryError):
        reader.read_adjusted_history(["AAPL"], date(2026, 1, 1), date(2026, 1, 31))


def test_reader_rejects_wrong_adjustment_basis(session: Session):
    repo = _seed(session)
    repo.upsert_bars(
        "AAPL",
        [PriceBar(date=date(2026, 1, 2), open=1, high=2, low=0.5, close=1.5, volume=10)],
        fetched_at=datetime(2026, 10, 14, tzinfo=timezone.utc),
        source="yfinance",
        interval="1d",
        adjustment_basis="raw",
        calendar="XNYS",
    )
    reader = StoredPriceHistoryReader(
        repo,
        required_interval="1d",
        required_adjustment_basis="split_dividend_adjusted",
        required_calendar="XNYS",
    )
    with pytest.raises(InvalidPriceHistoryError):
        reader.read_adjusted_history(["AAPL"], date(2026, 1, 1), date(2026, 1, 31))
