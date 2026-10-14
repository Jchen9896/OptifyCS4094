"""Optimization routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.optimization.service import OptimizationService, create_optimization_service
from app.schemas.optimization import OptimizationRequest, OptimizationResult

router = APIRouter(prefix="/optimizations", tags=["optimizations"])


def get_optimization_service(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> OptimizationService:
    return create_optimization_service(settings, db)


@router.post("", response_model=OptimizationResult)
def run_optimization(
    body: OptimizationRequest,
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationResult:
    """Optimize weights from stored prices for the requested tickers and period."""
    return service.run(
        body.tickers,
        body.start_date,
        body.end_date,
        strategy=body.strategy,
        max_weight=body.max_weight,
        risk_free_rate=body.risk_free_rate,
    )
