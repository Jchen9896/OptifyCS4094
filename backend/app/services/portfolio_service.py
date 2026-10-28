"""Rename and delete a portfolio for the user who owns it."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import (
    DuplicatePortfolioNameError,
    InvalidPortfolioNameError,
    PortfolioNotFoundError,
)
from app.models.portfolio import Portfolio
from app.repositories.portfolio_repository import PortfolioRepository


class PortfolioService:
    """Apply portfolio update and delete rules. The repository is injected."""

    def __init__(self, repository: PortfolioRepository) -> None:
        self._repository = repository

    def update_portfolio(self, portfolio_id: uuid.UUID, user_id: uuid.UUID, name: str) -> Portfolio:
        """Rename the portfolio when `user_id` owns it."""
        clean_name = name.strip()
        if not clean_name:
            raise InvalidPortfolioNameError()
        portfolio = self._require_owned(portfolio_id, user_id)
        if portfolio.name == clean_name:
            return portfolio
        try:
            return self._repository.rename(portfolio, clean_name)
        except IntegrityError as error:
            raise DuplicatePortfolioNameError() from error

    def delete_portfolio(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete the portfolio when `user_id` owns it."""
        portfolio = self._require_owned(portfolio_id, user_id)
        self._repository.delete(portfolio)

    def _require_owned(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Portfolio:
        portfolio = self._repository.get_for_user(portfolio_id, user_id)
        if portfolio is None:
            raise PortfolioNotFoundError()
        return portfolio


def create_portfolio_service(session: Session) -> PortfolioService:
    """Make a `PortfolioService` for the request session."""
    return PortfolioService(PortfolioRepository(session))
