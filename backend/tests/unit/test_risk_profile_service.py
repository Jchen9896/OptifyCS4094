"""Risk profile service: ownership, scoring, check, and replace (Decision 014)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.errors import InvalidRiskAnswersError, PortfolioNotFoundError, RiskProfileNotFoundError
from app.models.portfolio import Portfolio
from app.models.portfolio_position import PortfolioHolding
from app.models.portfolio_risk_profile import PortfolioRiskProfile
from app.models.stock import Stock
from app.models.user import User
from app.onboarding.questionnaire_loader import load_questionnaire
from app.onboarding.recommendation import RecommendationChecker
from app.onboarding.scoring import PointsRiskScorer
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.portfolio_risk_profile_repository import PortfolioRiskProfileRepository
from app.services.risk_profile_service import RiskProfileService

SETUP = {
    "initial_capital": 1000, "start_date": "2025-01-01", "end_date": "2026-01-01",
    "strategy": "min_variance", "max_weight": 1, "risk_free_rate": 0.04,
    "weights": {"AAPL": 50, "MSFT": 50}, "reference_prices": {"AAPL": 100, "MSFT": 200},
}


class FakeChecker(RecommendationChecker):
    def __init__(self):
        self.calls = []

    def check(self, recommendation, tickers, setup):
        self.calls.append((recommendation, tickers, setup))
        return recommendation.model_copy(update={"checked": True})


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


def add_portfolio(session: Session) -> Portfolio:
    owner = User(email="owner@example.com", password_hash="test-only")
    session.add_all([owner, Stock(symbol="AAPL", name="Apple"), Stock(symbol="MSFT", name="Microsoft")])
    session.flush()
    holdings = [PortfolioHolding(symbol=symbol, quantity=Decimal("1")) for symbol in ("AAPL", "MSFT")]
    portfolio = Portfolio(user_id=owner.id, name="Core", holdings=holdings, setup=SETUP)
    session.add(portfolio)
    session.flush()
    return portfolio


def service_for(session: Session, checker: FakeChecker) -> RiskProfileService:
    questionnaire = load_questionnaire()
    return RiskProfileService(
        PortfolioRiskProfileRepository(session), PortfolioRepository(session),
        questionnaire, PointsRiskScorer(questionnaire), checker,
    )


def answers(pick_highest: bool) -> dict[str, str]:
    choose = max if pick_highest else min
    return {
        question.id: choose(question.options, key=lambda option: option.points).id
        for question in load_questionnaire().questions
    }


def test_questionnaire_hides_points(session):
    payload = service_for(session, FakeChecker()).get_questionnaire().model_dump()
    assert payload["version"] == load_questionnaire().version
    assert "points" not in payload["questions"][0]["options"][0]


def test_save_scores_checks_and_stores(session):
    portfolio = add_portfolio(session)
    checker = FakeChecker()

    saved = service_for(session, checker).save_profile(portfolio.id, portfolio.user_id, answers(True))

    assert (saved.level, saved.label, saved.score) == ("aggressive", "Aggressive", 100)
    assert saved.recommendation.strategy == "target_risk"
    assert saved.recommendation.checked is True
    recommendation, tickers, setup = checker.calls[0]
    assert sorted(tickers) == ["AAPL", "MSFT"]
    assert setup.risk_free_rate == 0.04
    # The aggressive cap is 50%, which works for two stocks.
    assert recommendation.max_weight == 0.5


def test_save_again_replaces_and_get_reads_latest(session):
    portfolio = add_portfolio(session)
    service = service_for(session, FakeChecker())
    service.save_profile(portfolio.id, portfolio.user_id, answers(True))

    service.save_profile(portfolio.id, portfolio.user_id, answers(False))
    read = service.get_profile(portfolio.id, portfolio.user_id)

    assert read.level == "conservative"
    assert read.recommendation.strategy == "min_variance"
    assert session.scalar(select(func.count()).select_from(PortfolioRiskProfile)) == 1


def test_get_without_profile_raises(session):
    portfolio = add_portfolio(session)
    with pytest.raises(RiskProfileNotFoundError):
        service_for(session, FakeChecker()).get_profile(portfolio.id, portfolio.user_id)


def test_other_user_cannot_save_or_read(session):
    portfolio = add_portfolio(session)
    service = service_for(session, FakeChecker())
    with pytest.raises(PortfolioNotFoundError):
        service.save_profile(portfolio.id, uuid.uuid4(), answers(True))
    with pytest.raises(PortfolioNotFoundError):
        service.get_profile(portfolio.id, uuid.uuid4())


def test_invalid_answers_do_not_check_or_save(session):
    portfolio = add_portfolio(session)
    checker = FakeChecker()
    with pytest.raises(InvalidRiskAnswersError):
        service_for(session, checker).save_profile(portfolio.id, portfolio.user_id, {"goal": "growth"})
    assert checker.calls == []
    assert session.scalar(select(func.count()).select_from(PortfolioRiskProfile)) == 0


def test_portfolio_without_setup_passes_none(session):
    portfolio = add_portfolio(session)
    portfolio.setup = None
    session.flush()
    checker = FakeChecker()
    service_for(session, checker).save_profile(portfolio.id, portfolio.user_id, answers(False))
    assert checker.calls[0][2] is None
