"""Mean-variance optimization strategies."""

import cvxpy as cp
import numpy as np

from app.core.errors import OptimizationFailedError
from app.optimization.base import OptimizationStrategy
from app.optimization.constraints import (
    check_can_beat_risk_free_rate,
    check_rules_feasible,
    clean_weights,
    find_rule_violations,
    weight_constraints,
)

FAILURE_MESSAGE = (
    "The optimizer could not find a reliable allocation for this data. "
    "Try a longer date range or remove stocks that move almost the same way."
)


def _solve(problem: cp.Problem, solver: str) -> None:
    """Solve `problem` with `solver`.

    Raise `OptimizationFailedError` if the solver fails or the result is not fully accurate.
    """
    try:
        problem.solve(solver=solver)
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

    def __init__(self, tolerance: float, solver: str) -> None:
        self._tolerance = tolerance
        self._solver = solver

    def compute_weights(
        self,
        expected_returns: np.ndarray,
        covariance: np.ndarray,
        max_weight: float | None,
        risk_free_rate: float,
        *,
        target_return: float | None = None,
        target_volatility: float | None = None,
    ) -> np.ndarray:
        """Return the minimum-variance weights in ticker order.

        `expected_returns`, `risk_free_rate` and the targets are not used. The interface requires them,
        because other strategies use them. The inputs must already be checked by `validate_optimizer_input`.
        """
        asset_count = covariance.shape[0]
        check_rules_feasible(asset_count, max_weight, self._tolerance)

        weights = cp.Variable(asset_count)
        # validate_optimizer_input already checked the covariance matrix.
        # psd_wrap stops CVXPY from doing its own, stricter check, which can reject valid matrices.
        risk = cp.quad_form(weights, cp.psd_wrap(covariance))
        constraints = [cp.sum(weights) == 1, *weight_constraints(weights, max_weight)]
        _solve(cp.Problem(cp.Minimize(risk), constraints), self._solver)

        return _clean_and_check(weights.value, max_weight, self._tolerance)


class MaxSharpeStrategy(OptimizationStrategy):
    """Finds the allocation with the highest Sharpe ratio that follows the allocation rules.

    The Sharpe ratio is (expected return - risk-free rate) / volatility. CVXPY cannot maximize a ratio directly,
    so this strategy uses the Schaible transform (Palomar, section 7.2). It scales the weights so that the
    excess return is 1, finds the scaled weights with the lowest risk, and then scales them back.
    """

    name = "max_sharpe"

    def __init__(self, tolerance: float, solver: str) -> None:
        self._tolerance = tolerance
        self._solver = solver

    def compute_weights(
        self,
        expected_returns: np.ndarray,
        covariance: np.ndarray,
        max_weight: float | None,
        risk_free_rate: float,
        *,
        target_return: float | None = None,
        target_volatility: float | None = None,
    ) -> np.ndarray:
        """Return the maximum-Sharpe weights in ticker order.

        The targets are not used. The inputs must already be checked by `validate_optimizer_input`.
        """
        asset_count = covariance.shape[0]
        check_rules_feasible(asset_count, max_weight, self._tolerance)
        check_can_beat_risk_free_rate(expected_returns, risk_free_rate, max_weight, self._tolerance)

        # The real weights times one positive number. The rules below make the excess return exactly 1.
        scaled_weights = cp.Variable(asset_count)
        # psd_wrap: refer to MinimumVarianceStrategy.
        risk = cp.quad_form(scaled_weights, cp.psd_wrap(covariance))
        excess_returns = expected_returns - risk_free_rate
        constraints = [excess_returns @ scaled_weights == 1, *weight_constraints(scaled_weights, max_weight)]
        _solve(cp.Problem(cp.Minimize(risk), constraints), self._solver)

        # Divide by the total to get the real weights, which add up to 1.
        weights = scaled_weights.value / scaled_weights.value.sum()
        return _clean_and_check(weights, max_weight, self._tolerance)
