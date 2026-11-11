"""Authenticated create and read routes for saved optimization runs."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.current_user import get_current_user_id
from app.core.db import get_db
from app.schemas.optimization_run import (
    OptimizationRunCreateRequest,
    OptimizationRunDetailResponse,
    OptimizationRunSummaryResponse,
)
from app.services.optimization_run_service import (
    OptimizationRunService,
    create_optimization_run_service,
)

router = APIRouter(prefix="/portfolios", tags=["optimization-runs"])


def get_optimization_run_service(db: Session = Depends(get_db)) -> OptimizationRunService:
    return create_optimization_run_service(db)


@router.post(
    "/{portfolio_id}/optimization-runs",
    response_model=OptimizationRunDetailResponse,
    status_code=201,
)
def create_optimization_run(
    portfolio_id: uuid.UUID,
    body: OptimizationRunCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: OptimizationRunService = Depends(get_optimization_run_service),
) -> OptimizationRunDetailResponse:
    """Save one completed analysis for an owned portfolio."""
    return service.create_run(portfolio_id, user_id, body)


@router.get(
    "/{portfolio_id}/optimization-runs",
    response_model=list[OptimizationRunSummaryResponse],
)
def list_optimization_runs(
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: OptimizationRunService = Depends(get_optimization_run_service),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[OptimizationRunSummaryResponse]:
    """List recent runs for an owned portfolio, newest first."""
    return service.list_runs(portfolio_id, user_id, limit=limit)


@router.get(
    "/{portfolio_id}/optimization-runs/{run_id}",
    response_model=OptimizationRunDetailResponse,
)
def read_optimization_run(
    portfolio_id: uuid.UUID,
    run_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: OptimizationRunService = Depends(get_optimization_run_service),
) -> OptimizationRunDetailResponse:
    """Read one owned run. A wrong owner gets the same 404 as a missing run."""
    return service.get_run(portfolio_id, run_id, user_id)
