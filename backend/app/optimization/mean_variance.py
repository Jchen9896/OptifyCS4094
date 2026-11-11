"""Mean-variance optimization strategies."""

import cvxpy as cp
import numpy as np

from app.core.errors import InvalidOptimizationInputError, OptimizationFailedError
from app.optimization.base import OptimizationStrategy
from app.optimization.constraints import (
    check_can_beat_risk_free_rate,
    check_rules_feasible,
    check_target_return_reachable,
    check_target_volatility_reachable,
    clean_weights,
    find_rule_violations,
    highest_expected_return,
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


class TargetReturnStrategy(OptimizationStrategy):
    """Finds the allocation with the lowest risk whose expected return is at least the target.

    This is the mean-variance problem with a return target (Palomar, section 7.1.2, problem 7.3).
    The rule is "at least the target". Thus a target at or below the minimum-variance return gives
    the minimum-variance weights.
    """

    name = "target_return"

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
        """Return the lowest-risk weights with an expected return of at least `target_return`, in ticker order.

        `risk_free_rate` and `target_volatility` are not used. The inputs must already be checked by
        `validate_optimizer_input`.
        """
        if target_return is None:
            raise InvalidOptimizationInputError("The target_return strategy needs a target return.")
        asset_count = covariance.shape[0]
        check_rules_feasible(asset_count, max_weight, self._tolerance)
        check_target_return_reachable(expected_returns, target_return, max_weight, self._tolerance)
        # The check accepts a target up to the tolerance above the highest return. No allocation reaches
        # more than the highest return, so the solver gets the smaller of the two values.
        required_return = min(target_return, highest_expected_return(expected_returns, max_weight))

        weights = cp.Variable(asset_count)
        # psd_wrap: refer to MinimumVarianceStrategy.
        risk = cp.quad_form(weights, cp.psd_wrap(covariance))
        constraints = [
            cp.sum(weights) == 1,
            expected_returns @ weights >= required_return,
            *weight_constraints(weights, max_weight),
        ]
        _solve(cp.Problem(cp.Minimize(risk), constraints), self._solver)

        result = _clean_and_check(weights.value, max_weight, self._tolerance)
        if expected_returns @ result < target_return - self._tolerance:
            raise OptimizationFailedError(f"{FAILURE_MESSAGE} The result does not reach the target return.")
        return result

    def assumptions(
        self, *, target_return: float | None = None, target_volatility: float | None = None
    ) -> list[str]:
        """Return the line for the target return. `target_volatility` is not used."""
        if target_return is None:
            return []
        return [f"Target return: at least {target_return * 100:g}%."]


class TargetRiskStrategy(OptimizationStrategy):
    """Finds the allocation with the highest expected return whose volatility is at most the target.

    This is the mean-variance problem with a risk target (Palomar, section 7.1.2, problem 7.2).
    The rule is "at most the target". Thus a target at or above the volatility of the highest-return
    allocation gives that allocation.
    """

    name = "target_risk"

    def __init__(self, tolerance: float, solver: str) -> None:
        self._tolerance = tolerance
        self._solver = solver
        # The lowest volatility under the rules is the volatility of the minimum-variance allocation.
        self._minimum_variance = MinimumVarianceStrategy(tolerance, solver)

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
        """Return the highest-return weights with a volatility of at most `target_volatility`, in ticker order.

        `risk_free_rate` and `target_return` are not used. The inputs must already be checked by
        `validate_optimizer_input`.
        """
        if target_volatility is None:
            raise InvalidOptimizationInputError("The target_risk strategy needs a target volatility.")
        asset_count = covariance.shape[0]
        check_rules_feasible(asset_count, max_weight, self._tolerance)
        lowest_risk_weights = self._minimum_variance.compute_weights(
            expected_returns, covariance, max_weight, risk_free_rate
        )
        lowest_volatility = self._volatility(lowest_risk_weights, covariance)
        cap_binds = max_weight is not None and bool((lowest_risk_weights >= max_weight - self._tolerance).any())
        check_target_volatility_reachable(target_volatility, lowest_volatility, cap_binds, self._tolerance)
        # Near the lowest volatility, only the minimum-variance allocation follows the rules, and the solver
        # cannot solve the problem reliably. Thus the strategy gives the minimum-variance weights.
        if target_volatility <= lowest_volatility + self._tolerance:
            return lowest_risk_weights

        weights = cp.Variable(asset_count)
        # The covariance matrix is in a constraint, so psd_wrap does not work (Decision 005, "Target risk").
        # Use a factor F with F F' = covariance. Negative eigenvalues from rounding are set to 0, which can
        # only increase the risk of an allocation.
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        factor = eigenvectors * np.sqrt(np.clip(eigenvalues, 0.0, None))
        volatility = cp.norm(factor.T @ weights, 2)
        constraints = [
            cp.sum(weights) == 1,
            volatility <= target_volatility,
            *weight_constraints(weights, max_weight),
        ]
        _solve(cp.Problem(cp.Maximize(expected_returns @ weights), constraints), self._solver)

        result = _clean_and_check(weights.value, max_weight, self._tolerance)
        if self._volatility(result, covariance) > target_volatility + self._tolerance:
            raise OptimizationFailedError(f"{FAILURE_MESSAGE} The result is above the target volatility.")
        return result

    def assumptions(
        self, *, target_return: float | None = None, target_volatility: float | None = None
    ) -> list[str]:
        """Return the line for the target volatility. `target_return` is not used."""
        if target_volatility is None:
            return []
        return [f"Target volatility: at most {target_volatility * 100:g}%."]

    @staticmethod
    def _volatility(weights: np.ndarray, covariance: np.ndarray) -> float:
        """Return the volatility of `weights`. A variance below 0 from rounding counts as 0."""
        return float(np.sqrt(max(float(weights @ covariance @ weights), 0.0)))
