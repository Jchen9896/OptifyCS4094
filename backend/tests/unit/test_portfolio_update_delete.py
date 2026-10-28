"""Unit tests for portfolio rename and delete."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.core.errors import (
    DuplicatePortfolioNameError,
    InvalidPortfolioNameError,
    PortfolioNotFoundError,
)
from app.models.portfolio import Portfolio
from app.models.portfolio_position import PortfolioHolding
from app.models.stock import Stock
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.services.portfolio_service import PortfolioService


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()


def add_user(session: Session, email: str) -> User:
    user = User(email=email, password_hash="hash")
    session.add(user)
    session.flush()
    return user


def add_portfolio(session: Session, user: User, name: str) -> Portfolio:
    portfolio = Portfolio(user_id=user.id, name=name)
    session.add(portfolio)
    session.flush()
    return portfolio


def test_rename_changes_the_name_for_the_owner(session: Session):
    user = add_user(session, "owner@example.com")
    portfolio = add_portfolio(session, user, "Core")
    renamed = PortfolioRepository(session).rename(portfolio, "Growth")

    assert renamed.name == "Growth"
    assert session.get(Portfolio, portfolio.id).name == "Growth"


def test_rename_rejects_a_duplicate_name_for_the_same_user(session: Session):
    user = add_user(session, "owner@example.com")
    portfolio = add_portfolio(session, user, "Core")
    add_portfolio(session, user, "Growth")

    with pytest.raises(IntegrityError):
        PortfolioRepository(session).rename(portfolio, "Growth")


def test_rename_allows_the_same_name_for_another_user(session: Session):
    owner = add_user(session, "owner@example.com")
    other = add_user(session, "other@example.com")
    portfolio = add_portfolio(session, owner, "Core")
    add_portfolio(session, other, "Growth")

    renamed = PortfolioRepository(session).rename(portfolio, "Growth")

    assert renamed.name == "Growth"


def test_get_for_user_hides_a_portfolio_from_another_user(session: Session):
    owner = add_user(session, "owner@example.com")
    other = add_user(session, "other@example.com")
    portfolio = add_portfolio(session, owner, "Core")
    repo = PortfolioRepository(session)

    assert repo.get_for_user(portfolio.id, owner.id) is portfolio
    assert repo.get_for_user(portfolio.id, other.id) is None
    assert repo.get_for_user(uuid.uuid4(), owner.id) is None


def test_delete_removes_the_portfolio_and_its_holdings(session: Session):
    user = add_user(session, "owner@example.com")
    portfolio = add_portfolio(session, user, "Core")
    now = datetime.now(timezone.utc)
    session.add(Stock(symbol="AAPL", name="Apple Inc.", updated_at=now))
    session.add(
        PortfolioHolding(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            quantity=Decimal("1.500000"),
            added_at=now,
        )
    )
    session.flush()

    PortfolioRepository(session).delete(portfolio)
    session.expire_all()

    assert session.get(Portfolio, portfolio.id) is None
    rows = session.scalars(select(PortfolioHolding)).all()
    assert rows == []


class FakePortfolioRepository:
    def __init__(self, portfolio: Portfolio | None = None, error: Exception | None = None) -> None:
        self.portfolio = portfolio
        self.error = error
        self.renamed_to: str | None = None
        self.deleted = False

    def get_for_user(self, _portfolio_id: uuid.UUID, _user_id: uuid.UUID) -> Portfolio | None:
        return self.portfolio

    def rename(self, portfolio: Portfolio, name: str) -> Portfolio:
        if self.error:
            raise self.error
        portfolio.name = name
        self.renamed_to = name
        return portfolio

    def delete(self, _portfolio: Portfolio) -> None:
        self.deleted = True


def test_update_rejects_a_blank_name():
    service = PortfolioService(FakePortfolioRepository())

    with pytest.raises(InvalidPortfolioNameError):
        service.update_portfolio(uuid.uuid4(), uuid.uuid4(), "   ")


def test_update_reports_a_missing_portfolio():
    service = PortfolioService(FakePortfolioRepository())

    with pytest.raises(PortfolioNotFoundError):
        service.update_portfolio(uuid.uuid4(), uuid.uuid4(), "Growth")


def test_update_keeps_the_same_name_without_a_write():
    portfolio = Portfolio(id=uuid.uuid4(), user_id=uuid.uuid4(), name="Core")
    repo = FakePortfolioRepository(portfolio)
    service = PortfolioService(repo)

    result = service.update_portfolio(portfolio.id, portfolio.user_id, " Core ")

    assert result.name == "Core"
    assert repo.renamed_to is None


def test_update_renames_and_maps_a_duplicate_name():
    portfolio = Portfolio(id=uuid.uuid4(), user_id=uuid.uuid4(), name="Core")
    repo = FakePortfolioRepository(portfolio)
    updated = PortfolioService(repo).update_portfolio(portfolio.id, portfolio.user_id, "Growth")
    assert updated.name == "Growth"
    assert repo.renamed_to == "Growth"

    other = Portfolio(id=uuid.uuid4(), user_id=portfolio.user_id, name="Core")
    duplicate = FakePortfolioRepository(other, error=IntegrityError("dup", {}, Exception("dup")))
    with pytest.raises(DuplicatePortfolioNameError):
        PortfolioService(duplicate).update_portfolio(other.id, other.user_id, "Growth")


def test_delete_removes_an_owned_portfolio_and_rejects_a_missing_one():
    portfolio = Portfolio(id=uuid.uuid4(), user_id=uuid.uuid4(), name="Core")
    repo = FakePortfolioRepository(portfolio)
    PortfolioService(repo).delete_portfolio(portfolio.id, portfolio.user_id)
    assert repo.deleted is True

    missing = PortfolioService(FakePortfolioRepository())
    with pytest.raises(PortfolioNotFoundError):
        missing.delete_portfolio(uuid.uuid4(), uuid.uuid4())
