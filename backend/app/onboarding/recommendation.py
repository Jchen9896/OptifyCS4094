"""Make optimizer settings from a profile level, and check them on the portfolio (Decision 014)."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from app.core.errors import AppError, NoPositiveExcessReturnError, UnreachableTargetError
from app.optimization.service import OptimizationService
from app.schemas.onboarding import ProfileLevel, RiskRecommendation
from app.schemas.portfolio import PortfolioSetup


def base_recommendation(profile: ProfileLevel, holding_count: int) -> RiskRecommendation:
    """Return the level settings. Raise the weight cap when the holdings cannot add up to 100% under it."""
    notes = [f"{profile.label}: {profile.description}"]
    max_weight = profile.max_weight
    if holding_count > 0 and holding_count * max_weight < 1:
        # Round up to the next 0.1%, the same as the optimizer error message (constraints.check_rules_feasible).
        max_weight = math.ceil(1000 / holding_count) / 1000
        notes.append(
            f"With {holding_count} stocks, the maximum weight is {max_weight:.1%} "
            f"instead of {profile.max_weight:.0%}, so that the weights can add up to 100%."
        )
    return RiskRecommendation(
        strategy=profile.strategy,
        max_weight=max_weight,
        target_volatility=profile.target_volatility,
        notes=notes,
    )


class RecommendationChecker(ABC):
    """Checks a recommendation on the holdings of one portfolio."""

    @abstractmethod
    def check(
        self, recommendation: RiskRecommendation, tickers: list[str], setup: PortfolioSetup | None,
    ) -> RiskRecommendation:
        """Return the recommendation to show. It can be a different strategy, with a note that tells why."""


class OptimizerRecommendationChecker(RecommendationChecker):
    """Runs the recommended settings with the optimizer over the portfolio setup period."""

    # The optimizer raises these when the settings cannot work for these stocks. Minimum variance always can.
    _FALLBACK_ERRORS = (UnreachableTargetError, NoPositiveExcessReturnError)

    def __init__(self, optimization_service: OptimizationService) -> None:
        self._optimization_service = optimization_service

    def check(
        self, recommendation: RiskRecommendation, tickers: list[str], setup: PortfolioSetup | None,
    ) -> RiskRecommendation:
        if setup is None or len(tickers) < 2:
            return _with_note(
                recommendation,
                "Not checked: save the portfolio with at least two stocks and a history period first.",
            )
        try:
            self._run(recommendation, tickers, setup)
        except self._FALLBACK_ERRORS as error:
            return RiskRecommendation(
                strategy="min_variance",
                max_weight=recommendation.max_weight,
                target_volatility=None,
                checked=True,
                notes=[
                    *recommendation.notes,
                    f"The {recommendation.strategy} strategy does not work for these stocks: {error.message} "
                    "Minimum variance is recommended instead.",
                ],
            )
        except AppError as error:
            return _with_note(recommendation, f"Not checked: {error.message}")
        return recommendation.model_copy(update={"checked": True})

    def _run(self, recommendation: RiskRecommendation, tickers: list[str], setup: PortfolioSetup) -> None:
        self._optimization_service.run(
            tickers,
            setup.start_date,
            setup.end_date,
            strategy=recommendation.strategy,
            max_weight=recommendation.max_weight,
            risk_free_rate=setup.risk_free_rate,
            target_volatility=recommendation.target_volatility,
        )


def _with_note(recommendation: RiskRecommendation, note: str) -> RiskRecommendation:
    return recommendation.model_copy(update={"notes": [*recommendation.notes, note]})
