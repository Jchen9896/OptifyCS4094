"""Risk profile row. One portfolio has at most one profile (Decision 014)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, Uuid, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PortfolioRiskProfile(Base):
    """Questionnaire answers, scores, and the recommended optimizer settings for one portfolio."""

    __tablename__ = "portfolio_risk_profiles"
    __table_args__ = (
        UniqueConstraint("portfolio_id", name="portfolio_risk_profiles_portfolio_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    questionnaire_version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Question id -> option id, as the user submitted them.
    answers: Mapped[dict] = mapped_column(JSON, nullable=False)
    capacity_score: Mapped[float] = mapped_column(Float, nullable=False)
    willingness_score: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    # Recommended strategy settings and the reasons for them.
    recommendation: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
