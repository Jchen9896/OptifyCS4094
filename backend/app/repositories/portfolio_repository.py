"""Load, rename, and delete one portfolio. The session is injected for tests."""

import uuid

from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio
from app.models.portfolio_position import PortfolioHolding  # noqa: F401


class PortfolioRepository:
    """Update and delete a portfolio row. Create and list stay out of this class."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_user(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Portfolio | None:
        """Return the portfolio only when `user_id` owns it."""
        row = self._session.get(Portfolio, portfolio_id)
        if row is None or row.user_id != user_id:
            return None
        return row

    def rename(self, portfolio: Portfolio, name: str) -> Portfolio:
        """Set the portfolio name and flush so a duplicate name fails here."""
        portfolio.name = name
        self._session.flush()
        return portfolio

    def delete(self, portfolio: Portfolio) -> None:
        """Remove the portfolio. Holdings are removed with it."""
        self._session.delete(portfolio)
        self._session.flush()
