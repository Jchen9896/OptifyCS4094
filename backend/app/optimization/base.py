"""Shared interface for optimization strategies."""

from abc import ABC, abstractmethod

import numpy as np


class OptimizationStrategy(ABC):
    """Calculates portfolio weights from inputs that are already validated.

    All strategies get the same inputs and return weights in ticker order.
    """

    name: str

    @abstractmethod
    def compute_weights(
        self,
        expected_returns: np.ndarray,
        covariance: np.ndarray,
        max_weight: float | None,
    ) -> np.ndarray:
        """Return one weight for each stock. The weights add up to 1."""
