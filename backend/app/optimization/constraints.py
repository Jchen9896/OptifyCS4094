"""Allocation rules that every optimization strategy follows."""

import math

import cvxpy as cp
import numpy as np

from app.core.errors import InfeasibleAllocationRulesError, NoPositiveExcessReturnError, UnreachableTargetError


def check_rules_feasible(
    asset_count: int,
    max_weight: float | None,
    tolerance: float,
    min_weights: np.ndarray | None = None,
) -> None:
    """Raise `InfeasibleAllocationRulesError` if the weights cannot add up to 100% under the rules."""
    floors = np.zeros(asset_count) if min_weights is None else np.asarray(min_weights, dtype=float)
    if floors.shape != (asset_count,):
        raise InfeasibleAllocationRulesError(
            f"Minimum weights must have one value per stock ({asset_count}), not {floors.size}."
        )
    if np.any(floors < -tolerance):
        raise InfeasibleAllocationRulesError("Minimum weights cannot be negative.")
    total_floor = float(floors.sum())
    if total_floor > 1 + tolerance:
        raise InfeasibleAllocationRulesError(
            f"Required holdings need at least {total_floor:.1%} of the portfolio, which is more than 100%. "
            "Clear some Required marks or lower their floors."
        )
    if max_weight is not None:
        over_cap = floors > max_weight + tolerance
        if np.any(over_cap):
            raise InfeasibleAllocationRulesError(
                f"A required holding asks for more than the maximum weight of {max_weight:.1%}."
            )
        largest_total = asset_count * max_weight
        if largest_total < 1 - tolerance:
            # The smallest cap that works is 1 / asset_count. Round it up to the next 0.1% for the message.
            smallest_cap = math.ceil(1000 / asset_count) / 1000
            raise InfeasibleAllocationRulesError(
                f"With {asset_count} stocks and a maximum weight of {max_weight:.1%}, at most "
                f"{largest_total:.1%} of the money can be invested. "
                f"Use a maximum weight of at least {smallest_cap:.1%} or add more stocks."
            )


def highest_expected_return(
    expected_returns: np.ndarray,
    max_weight: float | None,
    min_weights: np.ndarray | None = None,
) -> float:
    """Return the highest expected return of an allocation that follows the rules.

    Call `check_rules_feasible` first.
    """
    asset_count = len(expected_returns)
    floors = np.zeros(asset_count) if min_weights is None else np.asarray(min_weights, dtype=float)
    cap = 1.0 if max_weight is None else max_weight
    allocation = floors.copy()
    remaining = 1.0 - float(floors.sum())
    room = np.maximum(cap - floors, 0.0)
    # After the floors, put leftover money in the stocks with the highest expected returns first.
    for index in np.argsort(-expected_returns):
        if remaining <= 0:
            break
        take = min(float(room[index]), remaining)
        allocation[index] += take
        remaining -= take
    return float(allocation @ expected_returns)


def check_can_beat_risk_free_rate(
    expected_returns: np.ndarray,
    risk_free_rate: float,
    max_weight: float | None,
    tolerance: float,
    min_weights: np.ndarray | None = None,
) -> None:
    """Raise `NoPositiveExcessReturnError` if no allocation under the rules is expected to beat the risk-free rate.

    Call `check_rules_feasible` first.
    """
    best_return = highest_expected_return(expected_returns, max_weight, min_weights)
    if best_return <= risk_free_rate + tolerance:
        message = (
            f"No allocation is expected to beat the risk-free rate of {risk_free_rate:.1%}. Under the "
            f"allocation rules, the highest expected return is {best_return:.1%}. "
            "Use minimum variance or add stocks with higher expected returns."
        )
        if max_weight is not None:
            message += " A larger maximum weight can also help."
        raise NoPositiveExcessReturnError(message)


def check_target_return_reachable(
    expected_returns: np.ndarray,
    target_return: float,
    max_weight: float | None,
    tolerance: float,
    min_weights: np.ndarray | None = None,
) -> None:
    """Raise `UnreachableTargetError` if no allocation under the rules has an expected return of at least the target.

    Call `check_rules_feasible` first.
    """
    best_return = highest_expected_return(expected_returns, max_weight, min_weights)
    if target_return > best_return + tolerance:
        # Round down to the next 0.1%. The check accepts targets up to the tolerance above the highest return,
        # so the suggested target is always accepted.
        suggestion = math.floor((best_return + tolerance) * 1000) / 1000
        message = (
            f"No allocation under the allocation rules reaches an expected return of {target_return * 100:g}%. "
            f"Choose a target of at most {suggestion:.1%}."
        )
        if max_weight is not None:
            message += " A larger maximum weight can also help."
        raise UnreachableTargetError(message)


def check_target_volatility_reachable(
    target_volatility: float, lowest_volatility: float, cap_binds: bool, tolerance: float
) -> None:
    """Raise `UnreachableTargetError` if no allocation under the rules has a volatility of at most the target.

    `lowest_volatility` is the volatility of the minimum-variance allocation. `cap_binds` is True if a weight
    of that allocation is at `max_weight`.
    """
    if target_volatility < lowest_volatility - tolerance:
        # Round up to the next 0.1%. The check accepts targets down to the tolerance below the lowest volatility,
        # so the suggested target is always accepted.
        suggestion = math.ceil((lowest_volatility - tolerance) * 1000) / 1000
        message = (
            f"No allocation under the allocation rules has a volatility of at most {target_volatility * 100:g}%. "
            f"Choose a target of at least {suggestion:.1%}."
        )
        if cap_binds:
            message += " A larger maximum weight can also help."
        raise UnreachableTargetError(message)


def weight_constraints(
    weights: cp.Variable,
    max_weight: float | None,
    min_weights: np.ndarray | None = None,
) -> list[cp.Constraint]:
    """Return the solver rules that do not depend on the size of `weights`.

    No weight is negative, no weight is more than `max_weight` of the total, and required holdings
    stay at least `min_weights` of the total. Each strategy adds one more size rule (for example
    "the weights add up to 1"). Using a share of `sum(weights)` keeps the same meaning for scaled
    Max-Sharpe variables.
    """
    constraints = [weights >= 0]
    total = cp.sum(weights)
    if max_weight is not None:
        constraints.append(weights <= max_weight * total)
    if min_weights is not None:
        floors = np.asarray(min_weights, dtype=float)
        for index, floor in enumerate(floors):
            if floor > 0:
                constraints.append(weights[index] >= float(floor) * total)
    return constraints


def clean_weights(weights: np.ndarray, tolerance: float) -> np.ndarray:
    """Return a copy of `weights` without rounding noise from the solver.

    Weights nearer to 0 than `tolerance` become 0. Then the weights are scaled so that they add up to 1.
    Larger negative weights stay, so that `find_rule_violations` can report them.
    """
    cleaned = np.where(np.abs(weights) < tolerance, 0.0, weights)
    return cleaned / cleaned.sum()


def find_rule_violations(
    weights: np.ndarray,
    max_weight: float | None,
    tolerance: float,
    min_weights: np.ndarray | None = None,
) -> list[str]:
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
    if min_weights is not None:
        floors = np.asarray(min_weights, dtype=float)
        below_count = int((weights + tolerance < floors).sum())
        if below_count:
            violations.append(f"Weights below a required minimum: {below_count}.")
    return violations
