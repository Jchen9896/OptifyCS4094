"""Repository for the one risk profile of a portfolio (Decision 014)."""

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.portfolio import Portfolio
from app.models.portfolio_risk_profile import PortfolioRiskProfile
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.portfolio_risk_profile_repository import PortfolioRiskProfileRepository


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


def add_portfolio(session: Session, name: str = "Core") -> Portfolio:
    user = User(email=f"{name.lower()}@example.com", password_hash="test-only")
    session.add(user)
    session.flush()
    portfolio = Portfolio(user_id=user.id, name=name)
    session.add(portfolio)
    session.flush()
    return portfolio


def save(repo: PortfolioRiskProfileRepository, portfolio: Portfolio, level: str = "moderate", score: float = 50):
    return repo.save(
        portfolio.id,
        questionnaire_version=1,
        answers={"goal": "growth"},
        capacity_score=score + 10,
        willingness_score=score,
        score=score,
        level=level,
        recommendation={"strategy": "target_risk", "max_weight": 0.35, "target_volatility": 0.12},
    )


def count_profiles(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(PortfolioRiskProfile))


def test_get_returns_none_without_a_profile(session):
    portfolio = add_portfolio(session)
    assert PortfolioRiskProfileRepository(session).get_for_portfolio(portfolio.id) is None


def test_save_creates_a_profile(session):
    portfolio = add_portfolio(session)
    repo = PortfolioRiskProfileRepository(session)

    created = save(repo, portfolio)
    found = repo.get_for_portfolio(portfolio.id)

    assert found is not None
    assert found.id == created.id
    assert found.answers == {"goal": "growth"}
    assert found.recommendation["strategy"] == "target_risk"
    assert (found.capacity_score, found.willingness_score, found.score) == (60, 50, 50)


def test_save_again_replaces_the_same_row(session):
    portfolio = add_portfolio(session)
    repo = PortfolioRiskProfileRepository(session)
    first = save(repo, portfolio)

    second = save(repo, portfolio, level="aggressive", score=90)

    assert second.id == first.id
    assert second.level == "aggressive"
    assert second.score == 90
    assert count_profiles(session) == 1


def test_profiles_are_separate_for_each_portfolio(session):
    safe = add_portfolio(session, "Safe")
    risky = add_portfolio(session, "Risky")
    repo = PortfolioRiskProfileRepository(session)

    save(repo, safe, level="conservative", score=10)
    save(repo, risky, level="aggressive", score=90)

    assert repo.get_for_portfolio(safe.id).level == "conservative"
    assert repo.get_for_portfolio(risky.id).level == "aggressive"


def test_database_allows_one_profile_per_portfolio(session):
    portfolio = add_portfolio(session)
    for _ in range(2):
        session.add(PortfolioRiskProfile(
            portfolio_id=portfolio.id, questionnaire_version=1, answers={}, capacity_score=0,
            willingness_score=0, score=0, level="conservative", recommendation={},
        ))
    with pytest.raises(IntegrityError):
        session.flush()


def test_deleting_the_portfolio_deletes_its_profile(session):
    portfolio = add_portfolio(session)
    save(PortfolioRiskProfileRepository(session), portfolio)
    session.commit()

    PortfolioRepository(session).delete(portfolio)
    session.expire_all()

    assert count_profiles(session) == 0
