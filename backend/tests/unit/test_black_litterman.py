"""Unit tests for the Black–Litterman expected returns."""

import numpy as np
import pytest

from app.core.config import Settings
from app.core.errors import InvalidOptimizationInputError
from app.optimization.black_litterman import BlackLittermanEstimator

# The values in config.py, not from a local .env file. Refer to Decision 009.
EQUITY_RISK_PREMIUM = Settings.model_fields["equity_risk_premium"].default
TAU = Settings.model_fields["black_litterman_tau"].default
MARKET_TICKER = Settings.model_fields["market_proxy_ticker"].default
RISK_FREE_RATE = 0.04

# Two stocks and the market. The market has a variance of 0.0256 (16% volatility).
HISTORICAL_RETURNS = np.array([0.06, 0.35])
MARKET_COVARIANCES = np.array([0.0208, 0.0336])
MARKET_VARIANCE = 0.0256


def estimator() -> BlackLittermanEstimator:
    return BlackLittermanEstimator(EQUITY_RISK_PREMIUM, TAU, MARKET_TICKER)


def test_one_year_of_history_matches_the_hand_formula():
    # beta = (0.8125, 1.3125), prior = beta x 5% = (0.040625, 0.065625), view = mean - 4% = (0.02, 0.31).
    # k = 0.05 x 1 year = 0.05, so the result is 4% + (prior + 0.05 x view) / 1.05.
    result = estimator().estimate(HISTORICAL_RETURNS, MARKET_COVARIANCES, MARKET_VARIANCE, 1.0, RISK_FREE_RATE)

    assert result == pytest.approx([0.0796428571, 0.1172619048])


def test_prior_is_the_equilibrium_return_of_the_market():
    # He and Litterman (1999): the equilibrium excess returns are delta x covariance x w_market, with
    # delta = premium / var(market). The third asset is the market, so w_market = (0, 0, 1).
    covariance = np.array([[0.0400, 0.0120, 0.0208], [0.0120, 0.0900, 0.0336], [0.0208, 0.0336, 0.0256]])
    delta = EQUITY_RISK_PREMIUM / covariance[2, 2]
    equilibrium = delta * covariance @ np.array([0.0, 0.0, 1.0])

    # With 0 years of history, the views have no weight. The result is the risk-free rate plus the prior.
    result = estimator().estimate(HISTORICAL_RETURNS, covariance[:2, 2], covariance[2, 2], 0.0, RISK_FREE_RATE)

    assert result - RISK_FREE_RATE == pytest.approx(equilibrium[:2])


def test_assumption_line_shows_the_weight_of_the_history():
    assert estimator().assumptions(1.0) == [
        "Expected returns: Black–Litterman. Prior: the risk-free rate plus each stock's beta to the market index "
        "(SPY) × the 5% U.S. equity risk premium. View: this period's average returns, with 4.8% of the weight "
        "for 1.0 years of history (τ 0.05)."
    ]


def test_market_without_price_movement_is_rejected():
    with pytest.raises(InvalidOptimizationInputError, match=MARKET_TICKER):
        estimator().estimate(HISTORICAL_RETURNS, np.zeros(2), 0.0, 1.0, RISK_FREE_RATE)
