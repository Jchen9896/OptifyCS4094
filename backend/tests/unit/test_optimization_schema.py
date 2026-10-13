"""Unit tests for the optimizer input schema."""

import pytest
from pydantic import ValidationError

from app.schemas.optimization import OptimizerInput


def make_values(**changes) -> dict:
    """Return the fields of a valid two-stock input. `changes` replace single fields."""
    values = {
        "tickers": ["AAA", "BBB"],
        "expected_returns": [0.25, 0.05],
        "covariance": [[0.04, 0.0], [0.0, 0.01]],
        "strategy": "min_variance",
        "period_start": "2021-01-01",
        "period_end": "2025-12-31",
    }
    values.update(changes)
    return values


def test_valid_input_is_accepted():
    data = OptimizerInput(**make_values())

    assert data.tickers == ["AAA", "BBB"]
    assert data.max_weight is None
    assert data.period_start.year == 2021


@pytest.mark.parametrize(
    "changes",
    [
        {"tickers": ["AAA"]},
        {"expected_returns": ["abc", 0.05]},
        {"max_weight": 0},
        {"max_weight": 1.5},
        {"period_start": "not a date"},
    ],
)
def test_bad_field_is_rejected(changes):
    with pytest.raises(ValidationError):
        OptimizerInput(**make_values(**changes))
