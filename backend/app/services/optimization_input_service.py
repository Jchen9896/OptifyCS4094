"""Prepare calculation results for the optimizer without choosing weights."""

from dataclasses import dataclass
from datetime import date
from math import isfinite

from pydantic import ValidationError

from app.core.errors import InvalidOptimizationInputError
from app.optimization.validation import validate_optimizer_input
from app.schemas.optimization import OptimizerInput
from app.services.calculation_service import ReturnSummary, calculate_risk_statistics


@dataclass(frozen=True)
class PreparedOptimization:
    """Validated optimizer input and the assumptions behind its statistics."""

    optimizer_input: OptimizerInput
    assumptions: tuple[str, ...]


def prepare_optimization(
    summary: ReturnSummary,
    *,
    period_start: date,
    period_end: date,
    strategy: str,
    tolerance: float,
    max_weight: float | None = None,
    risk_free_rate: float | None = None,
) -> PreparedOptimization:
    """Map a calculated return summary into the existing optimizer input.

    Returns and covariance are annualized. A supplied risk-free rate must be
    an annual decimal too. The caller chooses the strategy and constraints.
    This function does not load prices or run an optimization strategy.
    """
    if len(summary.tickers) < 2:
        raise InvalidOptimizationInputError("Select at least two stocks for optimization.")
    if not isfinite(tolerance) or tolerance < 0:
        raise InvalidOptimizationInputError("The validation tolerance must be finite and nonnegative.")
    if not strategy.strip():
        raise InvalidOptimizationInputError("Choose an optimization strategy.")
    if risk_free_rate is not None and not isfinite(risk_free_rate):
        raise InvalidOptimizationInputError("The annual risk-free rate must be finite.")
    if period_start >= period_end:
        raise InvalidOptimizationInputError("The start date must be before the end date.")
    if any(start < period_start or end > period_end for start, end in summary.intervals):
        raise InvalidOptimizationInputError("The return intervals must be within the selected dates.")

    risk = calculate_risk_statistics(summary)
    try:
        optimizer_input = OptimizerInput(
            tickers=list(summary.tickers),
            expected_returns=list(summary.annualized_mean_returns),
            covariance=[list(row) for row in risk.annualized_covariance],
            strategy=strategy,
            max_weight=max_weight,
            risk_free_rate=risk_free_rate,
            period_start=period_start,
            period_end=period_end,
        )
    except ValidationError as error:
        detail = error.errors()[0]
        field = ".".join(str(part) for part in detail["loc"])
        raise InvalidOptimizationInputError(f"Invalid {field}: {detail['msg']}") from error
    validate_optimizer_input(optimizer_input, tolerance)

    assumptions = (
        "Returns are historical simple returns over shared trading intervals.",
        "Expected returns are annualized arithmetic means, without compounding.",
        f"Annualization assumes {summary.annualization_factor:g} trading sessions per year.",
        "Covariance is annualized sample covariance, using observations minus one.",
        "Historical estimates do not guarantee future returns or risk.",
    )
    if risk_free_rate is not None:
        assumptions += (f"The supplied annual risk-free rate is {risk_free_rate:g} as a decimal.",)
    return PreparedOptimization(optimizer_input=optimizer_input, assumptions=assumptions)
