"""Unit tests for optimization run create, list, and ownership."""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.core.errors import OptimizationRunNotFoundError, PortfolioNotFoundError
from app.models.portfolio import Portfolio
from app.models.user import User
from app.repositories.optimization_run_repository import OptimizationRunRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.optimization import EquityCurvePointSchema, OptimizationResult
from app.schemas.optimization_run import OptimizationRunCreateRequest, OptimizationRunParams
from app.services.optimization_run_service import OptimizationRunService


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()


def add_user(session: Session) -> User:
    user = User(email="owner@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


def add_portfolio(session: Session, user: User, name: str = "Core") -> Portfolio:
    portfolio = Portfolio(user_id=user.id, name=name)
    session.add(portfolio)
    session.flush()
    return portfolio


def sample_request() -> OptimizationRunCreateRequest:
    return OptimizationRunCreateRequest(
        params=OptimizationRunParams(
            tickers=["AAPL", "MSFT"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 1),
            strategy="min_variance",
            max_weight=0.6,
            risk_free_rate=0.04,
            initial_capital=10000,
            current_weights=[0.5, 0.5],
        ),
        result=OptimizationResult(
            strategy="min_variance",
            weights={"AAPL": 0.4, "MSFT": 0.6},
            expected_return=0.08,
            volatility=0.12,
            sharpe_ratio=0.33,
            current_expected_return=0.07,
            current_volatility=0.14,
            current_sharpe_ratio=0.21,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 6, 1),
            assumptions=["sample"],
            initial_capital=10000,
            equity_curve=[
                EquityCurvePointSchema(
                    date=date(2025, 1, 2),
                    current_value=10000,
                    optimized_value=10020,
                )
            ],
        ),
    )


def service_for(session: Session) -> OptimizationRunService:
    return OptimizationRunService(
        OptimizationRunRepository(session),
        PortfolioRepository(session),
    )


def test_create_and_list_runs_for_owner(session: Session):
    user = add_user(session)
    portfolio = add_portfolio(session, user)
    service = service_for(session)

    created = service.create_run(portfolio.id, user.id, sample_request())
    rows = service.list_runs(portfolio.id, user.id)

    assert created.portfolio_id == portfolio.id
    assert created.params.strategy == "min_variance"
    assert created.result.weights["MSFT"] == 0.6
    assert len(rows) == 1
    assert rows[0].id == created.id
    assert rows[0].expected_return == 0.08


def test_get_run_hides_other_users_portfolio(session: Session):
    owner = add_user(session)
    other = User(email="other@example.com", password_hash="hash")
    session.add(other)
    session.flush()
    portfolio = add_portfolio(session, owner)
    service = service_for(session)
    created = service.create_run(portfolio.id, owner.id, sample_request())

    with pytest.raises(PortfolioNotFoundError):
        service.get_run(portfolio.id, created.id, other.id)


def test_get_run_rejects_unknown_run_id(session: Session):
    user = add_user(session)
    portfolio = add_portfolio(session, user)
    service = service_for(session)

    with pytest.raises(OptimizationRunNotFoundError):
        service.get_run(portfolio.id, uuid.uuid4(), user.id)


def test_create_rejects_unknown_portfolio(session: Session):
    user = add_user(session)
    service = service_for(session)

    with pytest.raises(PortfolioNotFoundError):
        service.create_run(uuid.uuid4(), user.id, sample_request())


def test_list_orders_newest_first(session: Session):
    user = add_user(session)
    portfolio = add_portfolio(session, user)
    repo = OptimizationRunRepository(session)
    older = repo.create(portfolio.id, {"strategy": "min_variance", "start_date": "2025-01-01", "end_date": "2025-02-01"}, {
        "strategy": "min_variance",
        "period_start": "2025-01-01",
        "period_end": "2025-02-01",
        "expected_return": 0.1,
        "volatility": 0.2,
        "sharpe_ratio": 0.3,
    })
    older.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    newer = repo.create(portfolio.id, {"strategy": "max_sharpe", "start_date": "2025-01-01", "end_date": "2025-02-01"}, {
        "strategy": "max_sharpe",
        "period_start": "2025-01-01",
        "period_end": "2025-02-01",
        "expected_return": 0.11,
        "volatility": 0.21,
        "sharpe_ratio": 0.4,
    })
    newer.created_at = datetime(2025, 2, 1, tzinfo=timezone.utc)
    session.flush()

    rows = service_for(session).list_runs(portfolio.id, user.id)

    assert [row.id for row in rows] == [newer.id, older.id]
