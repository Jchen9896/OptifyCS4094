"""Allocation rules that every optimization strategy follows."""

import math

import cvxpy as cp
import numpy as np

from app.core.errors import InfeasibleAllocationRulesError


def check_rules_feasible(asset_count: int, max_weight: float | None, tolerance: float) -> None:
    """Raise `InfeasibleAllocationRulesError` if the weights cannot add up to 100% under `max_weight`."""
    if max_weight is None:
        return
    largest_total = asset_count * max_weight
    if largest_total < 1 - tolerance:
        # The smallest cap that works is 1 / asset_count. Round it up to the next 0.1% for the message.
        smallest_cap = math.ceil(1000 / asset_count) / 1000
        raise InfeasibleAllocationRulesError(
            f"With {asset_count} stocks and a maximum weight of {max_weight:.1%}, at most "
            f"{largest_total:.1%} of the money can be invested. "
            f"Use a maximum weight of at least {smallest_cap:.1%} or add more stocks."
        )


def weight_constraints(weights: cp.Variable, max_weight: float | None) -> list[cp.Constraint]:
    """Return the solver rules that do not depend on the size of `weights`.

    No weight is negative, and no weight is more than `max_weight` of the total. Each strategy adds
    one more rule that sets the size, for example "the weights add up to 1".
    """
    constraints = [weights >= 0]
    if max_weight is not None:
        constraints.append(weights <= max_weight * cp.sum(weights))
    return constraints


def clean_weights(weights: np.ndarray, tolerance: float) -> np.ndarray:
    """Return a copy of `weights` without rounding noise from the solver.

    Weights nearer to 0 than `tolerance` become 0. Then the weights are scaled so that they add up to 1.
    Larger negative weights stay, so that `find_rule_violations` can report them.
    """
    cleaned = np.where(np.abs(weights) < tolerance, 0.0, weights)
    return cleaned / cleaned.sum()


def find_rule_violations(weights: np.ndarray, max_weight: float | None, tolerance: float) -> list[str]:
    """Return a description of each rule that `weights` break. An empty list means that all rules are met."""
    # Check this first. A comparison with NaN is always False, so NaN would pass the other checks.
    if not np.isfinite(weights).all():
        return ["The weights contain missing or infinite values."]

    violations = []
    total = weights.sum()
    if abs(total - 1) > tolerance:
        violations.append(f"The weights add up to {total:.6f}, not 1.")
    negative_count = int((weights < -tolerance).sum())
    if negative_count:
        violations.append(f"Negative weights: {negative_count}.")
    if max_weight is not None:
        above_count = int((weights > max_weight + tolerance).sum())
        if above_count:
            violations.append(f"Weights above the maximum weight of {max_weight:.1%}: {above_count}.")
    return violations
