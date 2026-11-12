"""Persist portfolio risk profiles through an injected session (Decision 014)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.portfolio_risk_profile import PortfolioRiskProfile


class PortfolioRiskProfileRepository:
    """Read and save the one risk profile of a portfolio."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_portfolio(self, portfolio_id: uuid.UUID) -> PortfolioRiskProfile | None:
        return self._session.scalar(
            select(PortfolioRiskProfile).where(PortfolioRiskProfile.portfolio_id == portfolio_id)
        )

    def save(
        self,
        portfolio_id: uuid.UUID,
        *,
        questionnaire_version: int,
        answers: dict[str, str],
        capacity_score: float,
        willingness_score: float,
        score: float,
        level: str,
        recommendation: dict,
    ) -> PortfolioRiskProfile:
        """Create the profile, or replace the values of the current profile."""
        row = self.get_for_portfolio(portfolio_id)
        if row is None:
            row = PortfolioRiskProfile(portfolio_id=portfolio_id)
            self._session.add(row)
        row.questionnaire_version = questionnaire_version
        row.answers = answers
        row.capacity_score = capacity_score
        row.willingness_score = willingness_score
        row.score = score
        row.level = level
        row.recommendation = recommendation
        self._session.flush()
        return row
