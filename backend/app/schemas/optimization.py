"""Optimizer input and result schemas."""

from datetime import date

from pydantic import BaseModel, Field


class OptimizerInput(BaseModel):
    """Inputs for one optimization run."""

    tickers: list[str] = Field(min_length=2)
    expected_returns: list[float]
    covariance: list[list[float]]
    strategy: str
    max_weight: float | None = Field(default=None, gt=0, le=1)
    risk_free_rate: float | None = None
    period_start: date
    period_end: date


class OptimizationResult(BaseModel):
    """A successful optimization run."""

    strategy: str
    weights: dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    period_start: date
    period_end: date
    assumptions: list[str]
