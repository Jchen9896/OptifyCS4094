"""Black–Litterman expected returns (Decision 009)."""

import numpy as np

from app.core.errors import InvalidOptimizationInputError


class BlackLittermanEstimator:
    """Calculates the expected returns that the strategies get, from the statistics of one period.

    The historical mean returns of one period have a large error. Thus the estimator starts from a prior and
    uses the historical mean returns only as views (He and Litterman, 1999):

    - Prior: the CAPM equilibrium excess return, beta x the equity risk premium. Beta is
      cov(stock, market) / var(market). This is equal to delta x covariance x w_market, with
      delta = premium / var(market). The uncertainty of the prior is tau x covariance.
    - View: the historical mean return minus the risk-free rate, one view for each stock. The uncertainty of
      a view is covariance / T, with T the years of history.

    Both uncertainties are multiples of the covariance matrix, so the matrix cancels. With k = tau x T:

        expected return = risk-free rate + (prior + k x view) / (1 + k)
    """

    def __init__(self, equity_risk_premium: float, tau: float, market_ticker: str) -> None:
        self._equity_risk_premium = equity_risk_premium
        self._tau = tau
        self._market_ticker = market_ticker

    @property
    def market_ticker(self) -> str:
        """The ticker of the market index for the prior."""
        return self._market_ticker

    def estimate(
        self,
        expected_returns: np.ndarray,
        market_covariances: np.ndarray,
        market_variance: float,
        years: float,
        risk_free_rate: float,
    ) -> np.ndarray:
        """Return the Black–Litterman expected returns in ticker order.

        `expected_returns` are the historical mean returns of the stocks. `market_covariances` are the
        covariances of the stocks with the market index, and `market_variance` is the variance of the market
        index. All values are yearly. `years` is the length of the shared daily returns, in years.
        """
        if market_variance <= 0:
            raise InvalidOptimizationInputError(
                f"The market index {self._market_ticker} has no price movement in this period."
            )
        betas = market_covariances / market_variance
        prior = betas * self._equity_risk_premium
        views = expected_returns - risk_free_rate
        # More years of history give the views more weight.
        history_strength = self._tau * years
        return risk_free_rate + (prior + history_strength * views) / (1 + history_strength)

    def assumptions(self, years: float) -> list[str]:
        """Return the line that tells how the expected returns were calculated."""
        history_strength = self._tau * years
        history_weight = history_strength / (1 + history_strength)
        return [
            "Expected returns: Black–Litterman. Prior: the risk-free rate plus each stock's beta to the market "
            f"index ({self._market_ticker}) × the {self._equity_risk_premium * 100:g}% U.S. equity risk premium. "
            f"View: this period's average returns, with {history_weight * 100:.1f}% of the weight for "
            f"{years:.1f} years of history (τ {self._tau:g})."
        ]
