"""Unit tests for the allocation rules."""

import cvxpy as cp
import numpy as np
import pytest

from app.core.errors import InfeasibleAllocationRulesError, NoPositiveExcessReturnError
from app.optimization.constraints import (
    check_can_beat_risk_free_rate,
    check_rules_feasible,
    clean_weights,
    find_rule_violations,
    weight_constraints,
)

# The planned setting. Refer to Decision 005.
TOLERANCE = 1e-5


@pytest.mark.parametrize(
    ("asset_count", "max_weight"),
    [(3, None), (3, 0.4), (3, 1 / 3), (4, 0.25), (2, 1.0)],
)
def test_feasible_rules_are_accepted(asset_count, max_weight):
    check_rules_feasible(asset_count, max_weight, TOLERANCE)


def test_infeasible_rules_are_rejected():
    with pytest.raises(InfeasibleAllocationRulesError, match="at most 90.0%") as error:
        check_rules_feasible(3, 0.3, TOLERANCE)

    assert "at least 33.4%" in error.value.message
    assert error.value.code == "infeasible_allocation_rules"
    assert error.value.status_code == 422


def test_total_just_below_100_percent_is_rejected():
    with pytest.raises(InfeasibleAllocationRulesError):
        check_rules_feasible(4, 0.2499, TOLERANCE)


@pytest.mark.parametrize(
    ("expected_returns", "max_weight"),
    [
        ([0.10, 0.02], None),  # All in the first stock: 10%.
        ([0.10, 0.01, 0.01], 0.4),  # Best under the cap: 0.4 x 10% + 0.4 x 1% + 0.2 x 1% = 4.6%.
    ],
)
def test_returns_that_can_beat_the_risk_free_rate_are_accepted(expected_returns, max_weight):
    check_can_beat_risk_free_rate(np.array(expected_returns), 0.04, max_weight, TOLERANCE)


@pytest.mark.parametrize(
    ("expected_returns", "max_weight", "risk_free_rate", "message"),
    [
        ([0.03, 0.02], None, 0.04, "highest expected return is 3.0%"),
        # One stock returns 10%, but the cap allows at most 0.34 x 10% + 0.34 x 1% + 0.32 x 1% = 4.06%.
        ([0.10, 0.01, 0.01], 0.34, 0.05, "highest expected return is 4.1%"),
    ],
)
def test_returns_that_cannot_beat_the_risk_free_rate_are_rejected(
    expected_returns, max_weight, risk_free_rate, message
):
    with pytest.raises(NoPositiveExcessReturnError, match=message) as error:
        check_can_beat_risk_free_rate(np.array(expected_returns), risk_free_rate, max_weight, TOLERANCE)

    assert error.value.code == "no_positive_excess_return"
    assert error.value.status_code == 422


@pytest.mark.parametrize(("max_weight", "expected_first_weight"), [(None, 1.0), (0.4, 0.4)])
def test_weight_constraints_limit_the_solver(max_weight, expected_first_weight):
    # Ask the solver to put as much as possible in the first stock. Only the rules can stop it.
    weights = cp.Variable(3)
    constraints = [cp.sum(weights) == 1, *weight_constraints(weights, max_weight)]
    problem = cp.Problem(cp.Maximize(weights[0]), constraints)
    problem.solve()

    assert weights.value[0] == pytest.approx(expected_first_weight, abs=TOLERANCE)
    assert weights.value.sum() == pytest.approx(1.0, abs=TOLERANCE)
    assert (weights.value >= -TOLERANCE).all()


def test_weight_constraints_work_at_any_size():
    # Max Sharpe solves with scaled weights. If the weights add up to 10, a 40% cap allows at most 4.
    weights = cp.Variable(3)
    constraints = [cp.sum(weights) == 10, *weight_constraints(weights, 0.4)]
    problem = cp.Problem(cp.Maximize(weights[0]), constraints)
    problem.solve()

    assert weights.value[0] / weights.value.sum() == pytest.approx(0.4, abs=TOLERANCE)


def test_clean_weights_removes_rounding_noise():
    # Noise of the size that OSQP can return.
    weights = np.array([0.6, 0.4 + 2e-6, -3e-6])

    cleaned = clean_weights(weights, TOLERANCE)

    assert cleaned[2] == 0.0
    assert cleaned.sum() == pytest.approx(1.0, abs=1e-15)
    assert weights[2] == -3e-6


def test_clean_weights_keeps_real_negative_weights():
    cleaned = clean_weights(np.array([1.1, -0.1]), TOLERANCE)

    assert cleaned[1] == pytest.approx(-0.1, abs=TOLERANCE)


def test_valid_weights_have_no_violations():
    assert find_rule_violations(np.array([0.4, 0.4, 0.2]), 0.4, TOLERANCE) == []


@pytest.mark.parametrize(
    ("weights", "max_weight", "message"),
    [
        ([0.5, 0.4], None, "add up to 0.900000"),
        ([1.2, -0.2], None, "Negative weights: 1."),
        ([1.00002, -0.00002], None, "Negative weights: 1."),
        ([0.5, 0.5], 0.4, "above the maximum weight of 40.0%: 2."),
        ([np.nan, 1.0], None, "missing or infinite"),
    ],
)
def test_broken_rules_are_reported(weights, max_weight, message):
    violations = find_rule_violations(np.array(weights), max_weight, TOLERANCE)

    assert any(message in violation for violation in violations)
