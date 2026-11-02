"""Portfolio update and delete routes."""

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.portfolio import PortfolioResponse, PortfolioUpdateRequest
from app.services.portfolio_service import PortfolioService, create_portfolio_service

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def get_portfolio_service(db: Session = Depends(get_db)) -> PortfolioService:
    return create_portfolio_service(db)


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
def update_portfolio(
    portfolio_id: uuid.UUID,
    body: PortfolioUpdateRequest,
    user_id: uuid.UUID,
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioResponse:
    """Rename a portfolio. `user_id` must own the portfolio."""
    portfolio = service.update_portfolio(portfolio_id, user_id, body.name)
    return PortfolioResponse.model_validate(portfolio)


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    service: PortfolioService = Depends(get_portfolio_service),
) -> Response:
    """Delete a portfolio. `user_id` must own the portfolio."""
    service.delete_portfolio(portfolio_id, user_id)
    return Response(status_code=204)
