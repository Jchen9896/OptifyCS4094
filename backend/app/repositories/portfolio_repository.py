"""Persist portfolios through an injected session."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.portfolio import Portfolio
from app.models.portfolio_position import PortfolioHolding
from app.models.user import User


class PortfolioRepository:
    """Create, read, rename, and delete owned portfolios."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_user(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Portfolio | None:
        """Return the portfolio only when `user_id` owns it."""
        return self._session.scalar(
            select(Portfolio)
            .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
            .options(selectinload(Portfolio.holdings).selectinload(PortfolioHolding.stock))
        )

    def user_exists(self, user_id: uuid.UUID) -> bool:
        return self._session.get(User, user_id) is not None

    def create(
        self, user_id: uuid.UUID, name: str, holdings: list[PortfolioHolding], setup: dict | None,
    ) -> Portfolio:
        row = Portfolio(user_id=user_id, name=name, holdings=holdings, setup=setup)
        self._session.add(row)
        self._session.flush()
        return row

    def list_for_user(self, user_id: uuid.UUID) -> list[Portfolio]:
        """Return only this user's portfolios, with a stable newest-first order."""
        return list(self._session.scalars(
            select(Portfolio).where(Portfolio.user_id == user_id)
            .order_by(Portfolio.created_at.desc(), Portfolio.id.desc())
        ))

    def rename(self, portfolio: Portfolio, name: str) -> Portfolio:
        """Set the portfolio name and flush so a duplicate name fails here."""
        portfolio.name = name
        self._session.flush()
        return portfolio

    def delete(self, portfolio: Portfolio) -> None:
        """Remove the portfolio. Holdings are removed with it."""
        self._session.delete(portfolio)
        self._session.flush()
