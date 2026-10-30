"""Shared interface for optimization strategies."""

from abc import ABC, abstractmethod

import numpy as np


class OptimizationStrategy(ABC):
    """Calculates portfolio weights from inputs that are already validated.

    All strategies get the same inputs and return weights in ticker order.
    A strategy ignores the inputs that it does not need.
    The targets are keyword-only, and `None` means "not given" (Decision 005, "Rules").
    """

    name: str

    @abstractmethod
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
        """Return one weight for each stock. The weights add up to 1."""

    def assumptions(
        self, *, target_return: float | None = None, target_volatility: float | None = None
    ) -> list[str]:
        """Return the lines that this strategy adds to the assumptions of a result. The default is no lines."""
        return []
