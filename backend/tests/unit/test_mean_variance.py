"""Unit tests for the mean-variance strategies."""

import cvxpy as cp
import numpy as np
import pytest

from app.core.config import Settings
from app.core.errors import (
    InfeasibleAllocationRulesError,
    InvalidOptimizationInputError,
    NoPositiveExcessReturnError,
    OptimizationFailedError,
    UnreachableTargetError,
)
from app.optimization.mean_variance import MaxSharpeStrategy, MinimumVarianceStrategy, TargetReturnStrategy

# The values in config.py, not from a local .env file. Refer to Decision 005.
TOLERANCE = Settings.model_fields["optimization_tolerance"].default
SOLVER = Settings.model_fields["optimization_solver"].default
RISK_FREE_RATE = 0.04
STRATEGIES = [MinimumVarianceStrategy, MaxSharpeStrategy, TargetReturnStrategy]

# A: 20% volatility, B: 10% volatility, correlation 0.
UNRELATED = np.array([[0.04, 0.0], [0.0, 0.01]])
THREE_STOCKS = np.array([[0.090, 0.010, 0.008], [0.010, 0.025, 0.006], [0.008, 0.006, 0.030]])


def run(
    strategy_class, covariance, max_weight=None, expected_returns=None, risk_free_rate=RISK_FREE_RATE, **targets
):
    """Run a strategy. By default every stock returns 10%, which beats the risk-free rate.

    Without `targets`, every allocation meets the targets: 1 point below the lowest expected return, and
    1 point above the highest volatility of one stock (a long-only allocation is never riskier than that).
    """
    expected_returns = np.full(len(covariance), 0.10) if expected_returns is None else np.asarray(expected_returns)
    if not targets:
        targets = {
            "target_return": expected_returns.min() - 0.01,
            "target_volatility": np.sqrt(np.diag(covariance)).max() + 0.01,
        }
    strategy = strategy_class(tolerance=TOLERANCE, solver=SOLVER)
    return strategy.compute_weights(expected_returns, covariance, max_weight, risk_free_rate, **targets)


def sharpe(weights, expected_returns, covariance):
    return (weights @ expected_returns - RISK_FREE_RATE) / np.sqrt(weights @ covariance @ weights)


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


@pytest.mark.parametrize("strategy_class", [MinimumVarianceStrategy, TargetReturnStrategy])
def test_cap_moves_the_answer_to_the_limit(strategy_class):
    # Without a cap the answer is 20/80. A 70% cap stops B at 70%, so A gets 30%.
    # Every allocation meets the default target return, so target return gives the minimum-variance answer.
    weights = run(strategy_class, UNRELATED, max_weight=0.7)

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


def test_max_sharpe_two_unrelated_stocks_match_the_hand_formula():
    # For unrelated stocks, each weight is proportional to (return - risk-free rate) / variance.
    # A: (0.12 - 0.04) / 0.04 = 2. B: (0.06 - 0.04) / 0.01 = 2. Equal scores give equal weights.
    weights = run(MaxSharpeStrategy, UNRELATED, expected_returns=[0.12, 0.06])

    assert weights == pytest.approx([0.5, 0.5], abs=TOLERANCE)


def test_max_sharpe_three_stocks_match_the_exact_formula():
    # Tangency portfolio: w = inverse(cov) (returns - risk-free rate), divided by its total.
    # The formula ignores the long-only rule. Here all of its weights are positive, so the answers must agree.
    expected_returns = np.array([0.12, 0.08, 0.10])
    solved = np.linalg.solve(THREE_STOCKS, expected_returns - RISK_FREE_RATE)
    exact = solved / solved.sum()
    assert (exact > 0).all()

    weights = run(MaxSharpeStrategy, THREE_STOCKS, expected_returns=expected_returns)

    assert weights == pytest.approx(exact, abs=TOLERANCE)


def test_max_sharpe_cap_moves_the_answer_to_the_limit():
    # Scores: A (0.16 - 0.04) / 0.04 = 3, B (0.06 - 0.04) / 0.01 = 2, so 60/40 without a cap.
    # A 50% cap stops A at 50%.
    uncapped = run(MaxSharpeStrategy, UNRELATED, expected_returns=[0.16, 0.06])
    capped = run(MaxSharpeStrategy, UNRELATED, max_weight=0.5, expected_returns=[0.16, 0.06])

    assert uncapped == pytest.approx([0.6, 0.4], abs=TOLERANCE)
    assert capped == pytest.approx([0.5, 0.5], abs=TOLERANCE)


def test_max_sharpe_gives_nothing_to_a_stock_below_the_risk_free_rate():
    # B returns 2%, less than the 4% risk-free rate. The formula would short B. With the long-only rule, B gets 0.
    weights = run(MaxSharpeStrategy, UNRELATED, expected_returns=[0.10, 0.02])

    assert weights == pytest.approx([1.0, 0.0], abs=TOLERANCE)


def test_max_sharpe_uses_the_risk_free_rate():
    # With a 4% risk-free rate the answer is 60/40 (see the cap test).
    # With 0%, the scores are A 0.16 / 0.04 = 4 and B 0.06 / 0.01 = 6, so 40/60.
    weights = run(MaxSharpeStrategy, UNRELATED, expected_returns=[0.16, 0.06], risk_free_rate=0.0)

    assert weights == pytest.approx([0.4, 0.6], abs=TOLERANCE)


def test_max_sharpe_is_never_worse_than_equal_weights_or_min_variance():
    rng = np.random.default_rng(seed=7)
    for _ in range(20):
        asset_count = int(rng.integers(2, 11))
        covariance = np.cov(rng.normal(0, 0.01, size=(300, asset_count)), rowvar=False) * 252
        # Every stock beats the 4% risk-free rate, so max Sharpe always has an answer.
        expected_returns = rng.uniform(0.05, 0.20, asset_count)
        max_weight = float(rng.uniform(1 / asset_count, 1.0))
        equal = np.full(asset_count, 1 / asset_count)

        best = run(MaxSharpeStrategy, covariance, max_weight, expected_returns)
        lowest_risk = run(MinimumVarianceStrategy, covariance, max_weight, expected_returns)

        # Both other portfolios follow the rules, so max Sharpe must be at least as good as each.
        best_sharpe = sharpe(best, expected_returns, covariance)
        assert best_sharpe >= sharpe(equal, expected_returns, covariance) - TOLERANCE
        assert best_sharpe >= sharpe(lowest_risk, expected_returns, covariance) - TOLERANCE
        assert best.sum() == pytest.approx(1.0, abs=TOLERANCE)
        assert (best <= max_weight + TOLERANCE).all()


def test_max_sharpe_rejects_returns_that_cannot_beat_the_risk_free_rate():
    with pytest.raises(NoPositiveExcessReturnError):
        run(MaxSharpeStrategy, UNRELATED, expected_returns=[0.03, 0.02])


def test_target_return_two_unrelated_stocks_match_the_hand_formula():
    # The return 12% w + 6% (1 - w) is at least 10% if w >= 2/3. The risk increases for w above 0.2
    # (refer to the first minimum-variance test), so the lowest risk is at w = 2/3.
    weights = run(TargetReturnStrategy, UNRELATED, expected_returns=[0.12, 0.06], target_return=0.10)

    assert weights == pytest.approx([2 / 3, 1 / 3], abs=TOLERANCE)


def test_target_return_three_stocks_match_the_exact_formula():
    # Palomar, section 7.1.2: without the long-only rule, the allocation for risk aversion lambda is
    # w = inverse(cov) (returns - g 1) / lambda, with g chosen so that the weights add up to 1. It has the
    # lowest risk for its own expected return, so a target of that return must give it. Here lambda = 3 and
    # all weights are positive, so the long-only rule does not change the answer.
    expected_returns = np.array([0.12, 0.08, 0.10])
    to_returns = np.linalg.solve(THREE_STOCKS, expected_returns)
    to_ones = np.linalg.solve(THREE_STOCKS, np.ones(3))
    g = (to_returns.sum() - 3.0) / to_ones.sum()
    exact = (to_returns - g * to_ones) / 3.0
    assert (exact > 0).all()

    weights = run(
        TargetReturnStrategy, THREE_STOCKS, expected_returns=expected_returns, target_return=exact @ expected_returns
    )

    assert weights == pytest.approx(exact, abs=TOLERANCE)


def test_target_return_above_the_highest_return_is_rejected():
    # With a 70% cap, the highest return is 70% x 12% + 30% x 6% = 10.2%.
    with pytest.raises(UnreachableTargetError, match="at most 10.2%"):
        run(TargetReturnStrategy, UNRELATED, max_weight=0.7, expected_returns=[0.12, 0.06], target_return=0.11)


@pytest.mark.parametrize("strategy_class", [TargetReturnStrategy])
def test_target_strategy_without_its_target_is_rejected(strategy_class):
    with pytest.raises(InvalidOptimizationInputError, match="needs a target"):
        run(strategy_class, UNRELATED, target_return=None, target_volatility=None)


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
