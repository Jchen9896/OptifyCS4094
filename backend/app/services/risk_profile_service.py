"""Score, check, save, and read the risk profile of an owned portfolio (Decision 014)."""

import uuid

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import PortfolioNotFoundError, RiskProfileNotFoundError
from app.models.portfolio import Portfolio
from app.models.portfolio_risk_profile import PortfolioRiskProfile
from app.onboarding.questionnaire_loader import load_questionnaire
from app.onboarding.recommendation import (
    OptimizerRecommendationChecker, RecommendationChecker, base_recommendation,
)
from app.onboarding.scoring import PointsRiskScorer, RiskScorer
from app.optimization.service import create_optimization_service
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.portfolio_risk_profile_repository import PortfolioRiskProfileRepository
from app.schemas.onboarding import Questionnaire, QuestionnaireResponse, RiskProfileResponse
from app.schemas.portfolio import PortfolioSetup


class RiskProfileService:
    """Apply ownership rules, then score the answers and check the recommendation."""

    def __init__(
        self,
        profiles: PortfolioRiskProfileRepository,
        portfolios: PortfolioRepository,
        questionnaire: Questionnaire,
        scorer: RiskScorer,
        checker: RecommendationChecker,
    ) -> None:
        self._profiles = profiles
        self._portfolios = portfolios
        self._questionnaire = questionnaire
        self._scorer = scorer
        self._checker = checker

    def get_questionnaire(self) -> QuestionnaireResponse:
        return QuestionnaireResponse.from_questionnaire(self._questionnaire)

    def save_profile(
        self, portfolio_id: uuid.UUID, user_id: uuid.UUID, answers: dict[str, str],
    ) -> RiskProfileResponse:
        """Score the answers before the check, so that bad answers do not start an optimization."""
        portfolio = self._require_owned_portfolio(portfolio_id, user_id)
        result = self._scorer.score(answers)
        tickers = [holding.symbol for holding in portfolio.holdings]
        setup = PortfolioSetup.model_validate(portfolio.setup) if portfolio.setup else None
        recommendation = self._checker.check(
            base_recommendation(result.profile, len(tickers)), tickers, setup,
        )
        row = self._profiles.save(
            portfolio_id,
            questionnaire_version=self._questionnaire.version,
            answers=dict(answers),
            capacity_score=result.capacity_score,
            willingness_score=result.willingness_score,
            score=result.score,
            level=result.profile.level,
            recommendation=recommendation.model_dump(mode="json"),
        )
        return self._to_response(row)

    def get_profile(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> RiskProfileResponse:
        self._require_owned_portfolio(portfolio_id, user_id)
        row = self._profiles.get_for_portfolio(portfolio_id)
        if row is None:
            raise RiskProfileNotFoundError()
        return self._to_response(row)

    def _require_owned_portfolio(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Portfolio:
        portfolio = self._portfolios.get_for_user(portfolio_id, user_id)
        if portfolio is None:
            raise PortfolioNotFoundError()
        return portfolio

    def _to_response(self, row: PortfolioRiskProfile) -> RiskProfileResponse:
        labels = {profile.level: profile.label for profile in self._questionnaire.profiles}
        return RiskProfileResponse.model_validate({
            "portfolio_id": row.portfolio_id,
            "questionnaire_version": row.questionnaire_version,
            "answers": row.answers,
            "capacity_score": row.capacity_score,
            "willingness_score": row.willingness_score,
            "score": row.score,
            "level": row.level,
            # A later questionnaire version can remove a level. Then show the stored level name.
            "label": labels.get(row.level, row.level),
            "recommendation": row.recommendation,
            "updated_at": row.updated_at,
        })


def create_risk_profile_service(settings: Settings, session: Session) -> RiskProfileService:
    """Make a `RiskProfileService` for the request session."""
    questionnaire = load_questionnaire()
    return RiskProfileService(
        PortfolioRiskProfileRepository(session),
        PortfolioRepository(session),
        questionnaire,
        PointsRiskScorer(questionnaire),
        OptimizerRecommendationChecker(create_optimization_service(settings, session)),
    )
