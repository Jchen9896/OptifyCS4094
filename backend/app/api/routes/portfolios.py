"""Portfolio create, read, update, and delete routes."""

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.portfolio import (
    PortfolioCreateRequest, PortfolioDetailResponse, PortfolioResponse, PortfolioUpdateRequest,
)
from app.services.portfolio_service import PortfolioService, create_portfolio_service

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def get_portfolio_service(db: Session = Depends(get_db)) -> PortfolioService:
    return create_portfolio_service(db)


@router.post("", response_model=PortfolioDetailResponse, status_code=201)
def create_portfolio(
    body: PortfolioCreateRequest, user_id: uuid.UUID,
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioDetailResponse:
    """Save a new portfolio for an existing user."""
    return PortfolioDetailResponse.model_validate(service.create_portfolio(user_id, body))


@router.get("", response_model=list[PortfolioResponse])
def list_portfolios(
    user_id: uuid.UUID, service: PortfolioService = Depends(get_portfolio_service),
) -> list[PortfolioResponse]:
    return [PortfolioResponse.model_validate(row) for row in service.list_portfolios(user_id)]


@router.get("/{portfolio_id}", response_model=PortfolioDetailResponse)
def read_portfolio(
    portfolio_id: uuid.UUID, user_id: uuid.UUID,
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioDetailResponse:
    """Read one portfolio. A wrong owner gets the same 404 as a missing row."""
    return PortfolioDetailResponse.model_validate(service.get_portfolio(portfolio_id, user_id))


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
