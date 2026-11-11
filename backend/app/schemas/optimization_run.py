"""HTTP schemas for persisted optimization runs."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.optimization import OptimizationResult


class OptimizationRunParams(BaseModel):
    """Stored optimizer request for one run."""

    model_config = ConfigDict(allow_inf_nan=False)

    tickers: list[str] = Field(min_length=2)
    start_date: date
    end_date: date
    strategy: str = "min_variance"
    max_weight: float | None = Field(default=None, gt=0, le=1)
    risk_free_rate: float | None = None
    target_return: float | None = None
    target_volatility: float | None = Field(default=None, gt=0)
    initial_capital: float | None = Field(default=None, gt=0)
    current_weights: list[float] | None = None
    reference_prices: dict[str, float] | None = None


class OptimizationRunCreateRequest(BaseModel):
    """Body to save one completed analysis for an owned portfolio."""

    params: OptimizationRunParams
    result: OptimizationResult


class OptimizationRunSummaryResponse(BaseModel):
    """List row for Compare and history selectors."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    portfolio_id: uuid.UUID
    strategy: str
    period_start: date
    period_end: date
    expected_return: float
    volatility: float
    sharpe_ratio: float
    created_at: datetime


class OptimizationRunDetailResponse(BaseModel):
    """Full stored run for Compare charts and tables."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    portfolio_id: uuid.UUID
    params: OptimizationRunParams
    result: OptimizationResult
    created_at: datetime
