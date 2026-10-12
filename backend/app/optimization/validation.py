"""Checks that the optimizer inputs make sense together before a strategy uses them."""

import numpy as np

from app.core.errors import InvalidOptimizationInputError
from app.schemas.optimization import OptimizerInput


def validate_optimizer_input(data: OptimizerInput, tolerance: float) -> tuple[np.ndarray, np.ndarray]:
    """Return the expected returns and the covariance matrix as NumPy arrays.

    Raise `InvalidOptimizationInputError` if the inputs do not make sense together.
    `tolerance` is the largest rounding error that the checks accept.
    """
    tickers = data.tickers
    count = len(tickers)

    duplicates = sorted({ticker for ticker in tickers if tickers.count(ticker) > 1})
    if duplicates:
        raise InvalidOptimizationInputError(f"These tickers appear more than once: {', '.join(duplicates)}.")
    if data.period_start >= data.period_end:
        raise InvalidOptimizationInputError("The start date must be before the end date.")
    if len(data.expected_returns) != count:
        raise InvalidOptimizationInputError(
            f"There are {count} tickers but {len(data.expected_returns)} expected returns."
        )
    # Check the row lengths before the conversion. NumPy cannot make an array from rows of different lengths.
    if len(data.covariance) != count or any(len(row) != count for row in data.covariance):
        raise InvalidOptimizationInputError(
            f"The covariance matrix must have {count} rows and {count} columns, one for each ticker."
        )

    expected_returns = np.asarray(data.expected_returns, dtype=float)
    covariance = np.asarray(data.covariance, dtype=float)

    if not (np.isfinite(expected_returns).all() and np.isfinite(covariance).all()):
        raise InvalidOptimizationInputError("The inputs contain missing or infinite values.")
    if not np.allclose(covariance, covariance.T, atol=tolerance):
        raise InvalidOptimizationInputError("The covariance matrix is not symmetric.")
    # A real covariance matrix never gives a portfolio a negative variance.
    # This is true only when its smallest eigenvalue is not negative.
    if np.linalg.eigvalsh(covariance).min() < -tolerance:
        raise InvalidOptimizationInputError(
            "The covariance matrix is not valid. It would give some portfolios a negative variance."
        )

    return expected_returns, covariance
