"""Request and response models for historical stock calculations."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.services.stored_calculation_service import CalculationResult


class CalculationRequest(BaseModel):
    tickers: list[str] = Field(min_length=1)
    start_date: date
    end_date: date


class ReturnInterval(BaseModel):
    start_date: date
    end_date: date


class SourceMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    retrieved_at: datetime
    adjustment_basis: str
    interval: str
    exchange: str
    calendar: str


class WarningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    message: str
    tickers: list[str]


class CalculationAssumptions(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    price_basis: str
    return_formula: str
    annualization_method: str
    annualization_factor: float
    sample_ddof: int
    calendar: str


class CalculationResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    tickers: list[str]
    start_date: date
    end_date: date
    intervals: list[ReturnInterval]
    daily_returns: list[list[float]]
    daily_mean_returns: list[float]
    annualized_mean_returns: list[float]
    daily_variances: list[float]
    annualized_variances: list[float]
    daily_covariance: list[list[float]]
    annualized_covariance: list[list[float]]
    correlation: list[list[float | None]]
    observation_count: int
    dropped_interval_count: int
    assumptions: CalculationAssumptions
    source_metadata: dict[str, SourceMetadata]
    warnings: list[WarningResponse]

    @classmethod
    def from_result(cls, result: CalculationResult) -> "CalculationResponse":
        """Convert calculation results into the public API response."""
        returns, risk = result.returns, result.risk
        return cls(
            tickers=returns.tickers,
            start_date=result.period_start,
            end_date=result.period_end,
            intervals=[
                ReturnInterval(start_date=start, end_date=end)
                for start, end in returns.intervals
            ],
            daily_returns=returns.daily_returns,
            daily_mean_returns=returns.daily_mean_returns,
            annualized_mean_returns=returns.annualized_mean_returns,
            daily_variances=risk.daily_variances,
            annualized_variances=risk.annualized_variances,
            daily_covariance=risk.daily_covariance,
            annualized_covariance=risk.annualized_covariance,
            correlation=risk.correlation,
            observation_count=returns.observation_count,
            dropped_interval_count=returns.dropped_interval_count,
            assumptions=CalculationAssumptions(
                price_basis="split_dividend_adjusted",
                return_formula="current_price / previous_price - 1",
                annualization_method="arithmetic",
                annualization_factor=returns.annualization_factor,
                sample_ddof=1,
                calendar=result.calendar,
            ),
            source_metadata={
                ticker: SourceMetadata.model_validate(data)
                for ticker, data in result.source_metadata.items()
            },
            warnings=[
                WarningResponse.model_validate(warning)
                for warning in result.warnings
            ],
        )
