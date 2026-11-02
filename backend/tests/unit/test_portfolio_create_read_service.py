"""Create/read rules with real repositories and injected ticker validation."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.errors import (
    DuplicatePortfolioNameError, InvalidPortfolioNameError, MarketDataUnavailableError,
    PortfolioNotFoundError, PortfolioUserNotFoundError, TickerNotFoundError, UnsupportedSecurityError,
)
from app.market_data.base import StockInfo
from app.models.portfolio import Portfolio
from app.models.stock import Stock
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.stock_repository import StockRepository
from app.schemas.portfolio import PortfolioCreateRequest
from app.services.portfolio_service import PortfolioService


class Tickers:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def validate_ticker(self, symbol):
        self.calls.append(symbol)
        if self.error and symbol == "FAIL":
            raise self.error
        return StockInfo(symbol=symbol, name=f"{symbol} Company", currency="USD", exchange="NMS", quote_type="EQUITY")


@pytest.fixture
def data():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(email="owner@example.com", password_hash="test-only")
        session.add(owner)
        session.commit()
        yield session, owner.id
    engine.dispose()


def service_for(session, tickers=None):
    return PortfolioService(PortfolioRepository(session), stock_service=tickers or Tickers(),
                            stock_repository=StockRepository(session))


def request(name="Core", symbols=("AAPL",)):
    return PortfolioCreateRequest(name=name, holdings=[{"symbol": s, "quantity": "1.25"} for s in symbols])


def test_create_trims_name_and_saves_validated_holdings(data):
    session, user_id = data
    tickers = Tickers()
    service = service_for(session, tickers)
    created = service.create_portfolio(user_id, request(" Core ", (" aapl ", "MSFT")))
    portfolio_id = created.id
    session.commit()
    session.expunge_all()
    saved = service.get_portfolio(portfolio_id, user_id)
    assert saved.name == "Core"
    assert tickers.calls == ["AAPL", "MSFT"]
    assert {h.symbol: h.quantity for h in saved.holdings} == {"AAPL": Decimal("1.25"), "MSFT": Decimal("1.25")}
    assert session.get(Stock, "AAPL").name == "AAPL Company"
    assert [p.id for p in service.list_portfolios(user_id)] == [saved.id]


def test_create_allows_empty_portfolio_and_same_name_for_another_user(data):
    session, user_id = data
    other = User(email="other@example.com", password_hash="test-only")
    session.add(other)
    session.flush()
    service = service_for(session)
    first = service.create_portfolio(user_id, request(symbols=()))
    second = service.create_portfolio(other.id, request(symbols=()))
    assert first.id != second.id
    assert first.holdings == []


def test_create_rejects_blank_name_and_unknown_user_before_validation(data):
    session, user_id = data
    tickers = Tickers()
    service = service_for(session, tickers)
    with pytest.raises(InvalidPortfolioNameError):
        service.create_portfolio(user_id, request("  "))
    with pytest.raises(PortfolioUserNotFoundError):
        service.create_portfolio(uuid.uuid4(), request())
    assert tickers.calls == []
    assert session.scalars(select(Portfolio)).all() == []


@pytest.mark.parametrize("error", [TickerNotFoundError("FAIL"), MarketDataUnavailableError(), UnsupportedSecurityError("FAIL", "OPTION")])
def test_later_ticker_failure_leaves_no_partial_writes(data, error):
    session, user_id = data
    with pytest.raises(type(error)):
        service_for(session, Tickers(error)).create_portfolio(user_id, request(symbols=("AAPL", "FAIL")))
    assert session.scalars(select(Stock)).all() == []
    assert session.scalars(select(Portfolio)).all() == []


def test_duplicate_name_maps_to_conflict_and_request_rollback_undoes_stock_write(data):
    session, user_id = data
    service = service_for(session)
    service.create_portfolio(user_id, request(symbols=()))
    session.commit()
    with pytest.raises(DuplicatePortfolioNameError):
        service.create_portfolio(user_id, request())
    session.rollback()
    assert session.get(Stock, "AAPL") is None
    assert len(service.list_portfolios(user_id)) == 1


def test_reads_hide_other_owners_and_do_not_call_ticker_validation(data):
    session, user_id = data
    tickers = Tickers()
    service = service_for(session, tickers)
    created = service.create_portfolio(user_id, request(symbols=()))
    for portfolio_id, owner_id in [(created.id, uuid.uuid4()), (uuid.uuid4(), user_id)]:
        with pytest.raises(PortfolioNotFoundError):
            service.get_portfolio(portfolio_id, owner_id)
    assert service.list_portfolios(uuid.uuid4()) == []
    assert tickers.calls == []


def test_unexpected_integrity_error_is_not_reported_as_duplicate_name(data, monkeypatch):
    session, user_id = data
    repo = PortfolioRepository(session)

    def fail(*args):
        raise IntegrityError("write", {}, Exception("unrelated constraint"))

    monkeypatch.setattr(repo, "create", fail)
    with pytest.raises(IntegrityError):
        PortfolioService(repo).create_portfolio(user_id, request(symbols=()))
