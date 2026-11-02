"""Create, read, rename, and delete portfolios for their owner."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    DuplicatePortfolioNameError,
    InvalidPortfolioNameError,
    PortfolioNotFoundError,
    PortfolioUserNotFoundError,
)
from app.models.portfolio import Portfolio
from app.models.portfolio_position import PortfolioHolding
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.stock_repository import StockRepository
from app.schemas.portfolio import PortfolioCreateRequest
from app.services.stock_service import StockService, create_stock_service


class PortfolioService:
    """Apply portfolio rules through injected repositories and ticker validation."""

    def __init__(
        self, repository: PortfolioRepository, *, stock_service: StockService | None = None,
        stock_repository: StockRepository | None = None,
    ) -> None:
        self._repository = repository
        self._stock_service = stock_service
        self._stock_repository = stock_repository

    def create_portfolio(self, user_id: uuid.UUID, request: PortfolioCreateRequest) -> Portfolio:
        """Validate all tickers first. The request session owns commit and rollback."""
        name = request.name.strip()
        if not name:
            raise InvalidPortfolioNameError()
        if not self._repository.user_exists(user_id):
            raise PortfolioUserNotFoundError()
        if request.holdings:
            if self._stock_service is None or self._stock_repository is None:
                raise ValueError("Stock dependencies are required to create holdings.")
            stocks = [self._stock_service.validate_ticker(item.symbol) for item in request.holdings]
            for stock in stocks:
                self._stock_repository.upsert(stock)
        holdings = [PortfolioHolding(symbol=item.symbol, quantity=item.quantity) for item in request.holdings]
        setup = request.setup.model_dump(mode="json") if request.setup is not None else None
        try:
            return self._repository.create(user_id, name, holdings, setup)
        except IntegrityError as error:
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint == "portfolios_user_id_name" or (
                "UNIQUE constraint failed: portfolios.user_id, portfolios.name" in str(error.orig)
            ):
                raise DuplicatePortfolioNameError() from error
            raise

    def get_portfolio(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Portfolio:
        return self._require_owned(portfolio_id, user_id)

    def list_portfolios(self, user_id: uuid.UUID) -> list[Portfolio]:
        return self._repository.list_for_user(user_id)

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
    return PortfolioService(
        PortfolioRepository(session), stock_service=create_stock_service(get_settings()),
        stock_repository=StockRepository(session),
    )
