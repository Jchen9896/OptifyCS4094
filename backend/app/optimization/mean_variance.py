"""Mean-variance optimization strategies."""

import cvxpy as cp
import numpy as np

from app.core.errors import OptimizationFailedError
from app.optimization.base import OptimizationStrategy
from app.optimization.constraints import (
    check_rules_feasible,
    clean_weights,
    find_rule_violations,
    weight_constraints,
)

FAILURE_MESSAGE = (
    "The optimizer could not find a reliable allocation for this data. "
    "Try a longer date range or remove stocks that move almost the same way."
)


def _solve(problem: cp.Problem) -> None:
    """Solve `problem`. Raise `OptimizationFailedError` if the solver fails or the result is not fully accurate."""
    try:
        # No solver is named, so CVXPY uses its default (OSQP for these problems).
        # For more accuracy, use problem.solve(solver="CLARABEL"). Refer to Decision 005.
        problem.solve()
    except cp.SolverError as error:
        raise OptimizationFailedError(FAILURE_MESSAGE) from error
    # Accept only a fully accurate result. "optimal_inaccurate" and all other statuses fail.
    if problem.status != cp.OPTIMAL:
        raise OptimizationFailedError(FAILURE_MESSAGE)


def _clean_and_check(weights: np.ndarray, max_weight: float | None, tolerance: float) -> np.ndarray:
    """Return `weights` without solver noise. Raise `OptimizationFailedError` if a rule is still broken."""
    result = clean_weights(weights, tolerance)
    violations = find_rule_violations(result, max_weight, tolerance)
    if violations:
        raise OptimizationFailedError(f"{FAILURE_MESSAGE} {' '.join(violations)}")
    return result


class MinimumVarianceStrategy(OptimizationStrategy):
    """Finds the allocation with the lowest risk (variance) that follows the allocation rules.

    This strategy uses only the covariance matrix. The expected returns do not change the weights.
    """

    name = "min_variance"

    def __init__(self, tolerance: float) -> None:
        self._tolerance = tolerance

    def compute_weights(
        self,
        expected_returns: np.ndarray,
        covariance: np.ndarray,
        max_weight: float | None,
        risk_free_rate: float,
    ) -> np.ndarray:
        """Return the minimum-variance weights in ticker order.

        `expected_returns` and `risk_free_rate` are not used. The interface requires them, because other
        strategies use them. The inputs must already be checked by `validate_optimizer_input`.
        """
        asset_count = covariance.shape[0]
        check_rules_feasible(asset_count, max_weight, self._tolerance)

        weights = cp.Variable(asset_count)
        # validate_optimizer_input already checked the covariance matrix.
        # psd_wrap stops CVXPY from doing its own, stricter check, which can reject valid matrices.
        risk = cp.quad_form(weights, cp.psd_wrap(covariance))
        constraints = [cp.sum(weights) == 1, *weight_constraints(weights, max_weight)]
        _solve(cp.Problem(cp.Minimize(risk), constraints))

        return _clean_and_check(weights.value, max_weight, self._tolerance)
