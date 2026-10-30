"""Validation and stored reads for portfolio creation."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.portfolio_position import PortfolioHolding
from app.models.stock import Stock
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import PortfolioCreateRequest, PortfolioDetailResponse, PortfolioSetup


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_create_and_read_from_a_new_session(session):
    user = User(email="owner@example.com", password_hash="test-only")
    stock = Stock(symbol="AAPL", name="Apple Inc.")
    session.add_all([user, stock])
    session.flush()
    repo = PortfolioRepository(session)
    assert repo.user_exists(user.id)
    assert not repo.user_exists(uuid.uuid4())
    portfolio = repo.create(user.id, "Core", [PortfolioHolding(symbol="AAPL", quantity=Decimal("1.5"))], None)
    portfolio_id, user_id = portfolio.id, user.id
    session.commit()
    session.expunge_all()
    saved = repo.get_for_user(portfolio_id, user_id)
    response = PortfolioDetailResponse.model_validate(saved)
    assert response.name == "Core"
    assert response.setup is None
    assert response.holdings[0].name == "Apple Inc."
    assert response.holdings[0].quantity == Decimal("1.500000")
    assert repo.get_for_user(portfolio_id, uuid.uuid4()) is None
    assert repo.get_for_user(uuid.uuid4(), user_id) is None


def test_list_filters_owner_and_orders_newest_first(session):
    owner = User(email="owner@example.com", password_hash="test-only")
    other = User(email="other@example.com", password_hash="test-only")
    session.add_all([owner, other])
    session.flush()
    repo = PortfolioRepository(session)
    older = repo.create(owner.id, "Older", [], None)
    older.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer = repo.create(owner.id, "Newer", [], None)
    repo.create(other.id, "Hidden", [], None)
    session.flush()
    assert [row.name for row in repo.list_for_user(owner.id)] == ["Newer", "Older"]
    assert repo.list_for_user(uuid.uuid4()) == []


def test_create_rejects_unknown_owner_and_duplicate_name(session):
    repo = PortfolioRepository(session)
    with pytest.raises(IntegrityError):
        repo.create(uuid.uuid4(), "Core", [], None)
    session.rollback()
    user = User(email="owner@example.com", password_hash="test-only")
    session.add(user)
    session.flush()
    repo.create(user.id, "Core", [], None)
    with pytest.raises(IntegrityError):
        repo.create(user.id, "Core", [], None)


@pytest.mark.parametrize("quantity", ["0", "-1", "NaN", "Infinity", "0.0000001", "1000000000000"])
def test_quantity_must_fit_the_storage_contract(quantity):
    with pytest.raises(ValidationError):
        PortfolioCreateRequest(name="Core", holdings=[{"symbol": "AAPL", "quantity": quantity}])


def test_create_normalizes_symbols_and_rejects_duplicates():
    request = PortfolioCreateRequest(name="Core", holdings=[{"symbol": " aapl ", "quantity": "1.5"}])
    assert request.holdings[0].symbol == "AAPL"
    with pytest.raises(ValidationError, match="duplicate"):
        PortfolioCreateRequest(name="Core", holdings=[
            {"symbol": "aapl", "quantity": 1}, {"symbol": " AAPL ", "quantity": 2},
        ])


def snapshot(**changes):
    return dict(initial_capital=1000, start_date="2026-01-01", end_date="2026-02-01",
                strategy="minvar", max_weight=1, risk_free_rate=0.04,
                weights={"AAPL": 100}, reference_prices={"AAPL": 100}, **changes)


@pytest.mark.parametrize(("field", "value"), [
    ("initial_capital", 0), ("max_weight", 2), ("risk_free_rate", float("inf")),
    ("weights", {"AAPL": -1}), ("reference_prices", {"AAPL": 0}),
    ("start_date", "2026-02-01"), ("strategy", "unknown"),
])
def test_snapshot_rejects_invalid_inputs(field, value):
    data = snapshot()
    data[field] = value
    with pytest.raises(ValidationError):
        PortfolioSetup(**data)


def test_snapshot_keys_must_match_holdings():
    with pytest.raises(ValidationError, match="match"):
        PortfolioCreateRequest(name="Core", setup=snapshot())
    request = PortfolioCreateRequest(name="Core", holdings=[{"symbol": "AAPL", "quantity": 10}], setup=snapshot())
    assert request.setup.model_dump(mode="json")["start_date"] == "2026-01-01"
