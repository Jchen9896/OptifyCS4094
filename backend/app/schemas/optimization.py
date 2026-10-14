"""Optimizer input and result schemas."""

from datetime import date

from pydantic import BaseModel, Field


class OptimizationRequest(BaseModel):
    """HTTP body for one optimization run from stored history."""

    tickers: list[str] = Field(min_length=2)
    start_date: date
    end_date: date
    strategy: str = "min_variance"
    max_weight: float | None = Field(default=None, gt=0, le=1)
    risk_free_rate: float | None = None
    # Current portfolio weights in ticker order (decimals that sum to 1). Used for charts.
    current_weights: list[float] | None = None


class OptimizerInput(BaseModel):
    """Inputs for one optimization run.

    `expected_returns`, `covariance` and `risk_free_rate` are yearly (annualized) values.
    """

    tickers: list[str] = Field(min_length=2)
    expected_returns: list[float]
    covariance: list[list[float]]
    strategy: str
    max_weight: float | None = Field(default=None, gt=0, le=1)
    risk_free_rate: float | None = None
    period_start: date
    period_end: date


class EquityCurvePointSchema(BaseModel):
    """One day on the current vs optimized capital path."""

    date: date
    current_value: float
    optimized_value: float


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
    initial_capital: float
    equity_curve: list[EquityCurvePointSchema]
