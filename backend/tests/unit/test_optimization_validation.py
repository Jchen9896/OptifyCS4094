"""Unit tests for the optimizer input checks."""

import numpy as np
import pytest

from app.core.errors import InvalidOptimizationInputError
from app.optimization.validation import validate_optimizer_input
from app.schemas.optimization import OptimizerInput

TOLERANCE = 1e-5


def make_input(**changes) -> OptimizerInput:
    """Return a valid two-stock input. `changes` replace single fields."""
    values = {
        "tickers": ["AAA", "BBB"],
        "expected_returns": [0.25, 0.05],
        "covariance": [[0.04, 0.0], [0.0, 0.01]],
        "strategy": "min_variance",
        "period_start": "2021-01-01",
        "period_end": "2025-12-31",
    }
    values.update(changes)
    return OptimizerInput(**values)


def test_valid_input_returns_arrays():
    expected_returns, covariance = validate_optimizer_input(make_input(), TOLERANCE)

    assert isinstance(expected_returns, np.ndarray)
    assert expected_returns.shape == (2,)
    assert covariance.shape == (2, 2)
    assert covariance[0, 0] == 0.04


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"tickers": ["AAA", "AAA"]}, "more than once: AAA"),
        ({"period_start": "2025-12-31", "period_end": "2021-01-01"}, "start date must be before"),
        ({"expected_returns": [0.25]}, "2 tickers but 1 expected returns"),
        ({"covariance": [[0.04, 0.0]]}, "2 rows and 2 columns"),
        ({"covariance": [[0.04, 0.0], [0.0]]}, "2 rows and 2 columns"),
        ({"expected_returns": [float("nan"), 0.05]}, "missing or infinite"),
        ({"covariance": [[0.04, 0.0], [0.0, float("inf")]]}, "missing or infinite"),
        ({"covariance": [[0.04, 0.01], [0.0, 0.01]]}, "not symmetric"),
        ({"covariance": [[0.04, 0.05], [0.05, 0.01]]}, "not valid"),
        ({"covariance": [[-0.04, 0.0], [0.0, 0.01]]}, "not valid"),
    ],
)
def test_bad_input_is_rejected(changes, message):
    with pytest.raises(InvalidOptimizationInputError, match=message) as error:
        validate_optimizer_input(make_input(**changes), TOLERANCE)

    assert error.value.code == "invalid_optimization_input"
    assert error.value.status_code == 422
