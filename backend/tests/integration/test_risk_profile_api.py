"""HTTP routes for the risk questionnaire and per-portfolio profiles (Decision 014)."""

import uuid

import pytest
from fastapi import Depends, Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.onboarding import get_risk_profile_service
from app.core.current_user import get_current_user_id
from app.core.db import Base, get_db
from app.main import create_app
from app.models.portfolio import Portfolio
from app.models.user import User
from app.onboarding.questionnaire_loader import load_questionnaire
from app.onboarding.recommendation import RecommendationChecker
from app.onboarding.scoring import PointsRiskScorer
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.portfolio_risk_profile_repository import PortfolioRiskProfileRepository
from app.services.risk_profile_service import RiskProfileService


class PassingChecker(RecommendationChecker):
    def check(self, recommendation, tickers, setup):
        return recommendation.model_copy(update={"checked": True})


@pytest.fixture
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(email="owner@example.com", password_hash="test-only")
        session.add(owner)
        session.flush()
        safe = Portfolio(user_id=owner.id, name="Safe")
        risky = Portfolio(user_id=owner.id, name="Risky")
        session.add_all([safe, risky])
        session.commit()
        ids = {"user": owner.id, "safe": str(safe.id), "risky": str(risky.id)}

    def database():
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def current_user(authorization: str = Header(default="")):
        return ids["user"] if authorization == "Bearer owner" else uuid.uuid4()

    def service(db=Depends(get_db)):
        questionnaire = load_questionnaire()
        return RiskProfileService(
            PortfolioRiskProfileRepository(db), PortfolioRepository(db),
            questionnaire, PointsRiskScorer(questionnaire), PassingChecker(),
        )

    app = create_app()
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user_id] = current_user
    app.dependency_overrides[get_risk_profile_service] = service
    with TestClient(app) as client:
        yield client, {"Authorization": "Bearer owner"}, ids
    engine.dispose()


def answers(client, headers, pick_highest: bool) -> dict[str, str]:
    questions = client.get("/api/onboarding/questionnaire", headers=headers).json()["questions"]
    # Option order in the file goes from the least to the most risk.
    return {question["id"]: question["options"][-1 if pick_highest else 0]["id"] for question in questions}


def test_questionnaire_has_no_points(api):
    client, owner, _ids = api
    response = client.get("/api/onboarding/questionnaire", headers=owner)
    assert response.status_code == 200
    option = response.json()["questions"][0]["options"][0]
    assert set(option) == {"id", "label"}


def test_each_portfolio_keeps_its_own_profile(api):
    client, owner, ids = api
    safe = client.put(
        f'/api/portfolios/{ids["safe"]}/risk-profile', headers=owner,
        json={"answers": answers(client, owner, pick_highest=False)},
    )
    risky = client.put(
        f'/api/portfolios/{ids["risky"]}/risk-profile', headers=owner,
        json={"answers": answers(client, owner, pick_highest=True)},
    )
    assert safe.status_code == risky.status_code == 200
    assert client.get(f'/api/portfolios/{ids["safe"]}/risk-profile', headers=owner).json()["level"] == "conservative"
    read = client.get(f'/api/portfolios/{ids["risky"]}/risk-profile', headers=owner).json()
    assert read["level"] == "aggressive"
    assert read["recommendation"]["strategy"] == "target_risk"
    assert read["recommendation"]["checked"] is True


def test_missing_profile_and_other_owner_return_404(api):
    client, owner, ids = api
    missing = client.get(f'/api/portfolios/{ids["safe"]}/risk-profile', headers=owner)
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "risk_profile_not_found"
    outsider = client.put(
        f'/api/portfolios/{ids["safe"]}/risk-profile', headers={"Authorization": "Bearer outsider"},
        json={"answers": answers(client, owner, pick_highest=True)},
    )
    assert outsider.status_code == 404
    assert outsider.json()["detail"]["code"] == "portfolio_not_found"


def test_invalid_answers_return_422(api):
    client, owner, ids = api
    response = client.put(f'/api/portfolios/{ids["safe"]}/risk-profile', headers=owner, json={"answers": {}})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_risk_answers"


def test_export_includes_risk_profile(api):
    client, owner, ids = api
    client.put(
        f'/api/portfolios/{ids["risky"]}/risk-profile', headers=owner,
        json={"answers": answers(client, owner, pick_highest=True)},
    )
    portfolios = {row["name"]: row for row in client.get("/api/account/export", headers=owner).json()["portfolios"]}
    assert portfolios["Safe"]["risk_profile"] is None
    assert portfolios["Risky"]["risk_profile"]["level"] == "aggressive"
