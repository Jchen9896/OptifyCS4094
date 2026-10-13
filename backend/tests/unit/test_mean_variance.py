"""Unit tests for the mean-variance strategies."""

import cvxpy as cp
import numpy as np
import pytest

from app.core.errors import InfeasibleAllocationRulesError, OptimizationFailedError
from app.optimization.mean_variance import MinimumVarianceStrategy

# The planned setting. Refer to Decision 005.
TOLERANCE = 1e-5
RISK_FREE_RATE = 0.04
STRATEGIES = [MinimumVarianceStrategy]

# A: 20% volatility, B: 10% volatility, correlation 0.
UNRELATED = np.array([[0.04, 0.0], [0.0, 0.01]])
THREE_STOCKS = np.array([[0.090, 0.010, 0.008], [0.010, 0.025, 0.006], [0.008, 0.006, 0.030]])


def run(strategy_class, covariance, max_weight=None, expected_returns=None, risk_free_rate=RISK_FREE_RATE):
    """Run a strategy. By default every stock returns 10%, which beats the risk-free rate."""
    if expected_returns is None:
        expected_returns = np.full(len(covariance), 0.10)
    strategy = strategy_class(tolerance=TOLERANCE)
    return strategy.compute_weights(np.asarray(expected_returns), covariance, max_weight, risk_free_rate)


def test_two_unrelated_stocks_match_the_hand_formula():
    # w_A = (var_B - cov_AB) / (var_A + var_B - 2 cov_AB) = 0.01 / 0.05 = 0.2
    weights = run(MinimumVarianceStrategy, UNRELATED)

    assert weights == pytest.approx([0.2, 0.8], abs=TOLERANCE)


def test_three_stocks_match_the_exact_formula():
    # Palomar, equation (6.15): w = inverse(cov) 1 / (1' inverse(cov) 1).
    # The formula ignores the long-only rule. Here all of its weights are positive, so the answers must agree.
    solved = np.linalg.solve(THREE_STOCKS, np.ones(3))
    exact = solved / solved.sum()
    assert (exact > 0).all()

    weights = run(MinimumVarianceStrategy, THREE_STOCKS)

    assert weights == pytest.approx(exact, abs=TOLERANCE)


def test_cap_moves_the_answer_to_the_limit():
    # Without a cap the answer is 20/80. A 70% cap stops B at 70%, so A gets 30%.
    weights = run(MinimumVarianceStrategy, UNRELATED, max_weight=0.7)

    assert weights == pytest.approx([0.3, 0.7], abs=TOLERANCE)


def test_long_only_rule_sets_a_weight_to_zero():
    # A: 30% volatility, B: 10% volatility, correlation 0.9.
    # Without the long-only rule, the exact formula gives A about -37%. With the rule, 100% B is best.
    covariance = np.array([[0.09, 0.027], [0.027, 0.01]])

    weights = run(MinimumVarianceStrategy, covariance)

    assert weights == pytest.approx([0.0, 1.0], abs=TOLERANCE)


def test_cap_of_one_over_n_gives_equal_weights():
    weights = run(MinimumVarianceStrategy, THREE_STOCKS, max_weight=1 / 3)

    assert weights == pytest.approx([1 / 3] * 3, abs=TOLERANCE)


def test_result_is_never_riskier_than_equal_weights():
    rng = np.random.default_rng(seed=7)
    for _ in range(20):
        asset_count = int(rng.integers(2, 11))
        # Daily returns of about 1%. Multiply by 252 to get yearly values, as the optimizer expects.
        covariance = np.cov(rng.normal(0, 0.01, size=(300, asset_count)), rowvar=False) * 252
        max_weight = float(rng.uniform(1 / asset_count, 1.0))
        equal = np.full(asset_count, 1 / asset_count)

        weights = run(MinimumVarianceStrategy, covariance, max_weight=max_weight)

        assert weights @ covariance @ weights <= equal @ covariance @ equal + TOLERANCE
        assert weights.sum() == pytest.approx(1.0, abs=TOLERANCE)
        assert (weights >= 0).all()
        assert (weights <= max_weight + TOLERANCE).all()


# The tests below apply to every strategy.


@pytest.mark.parametrize("strategy_class", STRATEGIES)
def test_nearly_identical_stocks_are_solved(strategy_class):
    # This test protects psd_wrap. Two stocks that move the same way (for example GOOG and GOOGL),
    # plus rounding noise, give a smallest eigenvalue of -1e-8. validate_optimizer_input accepts it.
    # Without psd_wrap, CVXPY rejects matrices below about -1e-10 with an error that we do not catch.
    covariance = np.array([[0.01, 0.01 + 1e-8], [0.01 + 1e-8, 0.01]])

    weights = run(strategy_class, covariance)

    assert weights.sum() == pytest.approx(1.0, abs=TOLERANCE)


@pytest.mark.parametrize("strategy_class", STRATEGIES)
def test_impossible_cap_is_rejected(strategy_class):
    with pytest.raises(InfeasibleAllocationRulesError):
        run(strategy_class, THREE_STOCKS, max_weight=0.3)


@pytest.mark.parametrize("strategy_class", STRATEGIES)
def test_solver_crash_gives_a_clear_error(strategy_class, monkeypatch):
    def crash(*args, **kwargs):
        raise cp.SolverError("Simulated crash.")

    monkeypatch.setattr(cp.Problem, "solve", crash)

    with pytest.raises(OptimizationFailedError, match="could not find a reliable allocation") as error:
        run(strategy_class, UNRELATED)

    assert error.value.code == "optimization_failed"
    assert error.value.status_code == 422


@pytest.mark.parametrize("strategy_class", STRATEGIES)
def test_result_that_is_not_optimal_is_rejected(strategy_class, monkeypatch):
    # The fake solve does nothing, so the status is not "optimal".
    monkeypatch.setattr(cp.Problem, "solve", lambda *args, **kwargs: None)

    with pytest.raises(OptimizationFailedError):
        run(strategy_class, UNRELATED)


@pytest.mark.parametrize("strategy_class", STRATEGIES)
def test_weights_that_break_the_rules_are_rejected(strategy_class, monkeypatch):
    monkeypatch.setattr(
        "app.optimization.mean_variance.find_rule_violations",
        lambda *args: ["Negative weights: 1."],
    )

    with pytest.raises(OptimizationFailedError, match="Negative weights: 1."):
        run(strategy_class, UNRELATED)
