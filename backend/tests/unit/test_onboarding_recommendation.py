"""Recommendation settings and the optimizer check (Decision 014)."""

from datetime import date

import pytest

from app.core.errors import (
    InsufficientHistoryError, NoPositiveExcessReturnError, UnreachableTargetError,
)
from app.onboarding.recommendation import OptimizerRecommendationChecker, base_recommendation
from app.schemas.onboarding import ProfileLevel
from app.schemas.portfolio import PortfolioSetup

TICKERS = ["AAPL", "MSFT", "SPY"]


def moderate() -> ProfileLevel:
    return ProfileLevel(
        level="moderate", label="Moderate", min_score=40, description="Balanced.",
        strategy="target_risk", max_weight=0.35, target_volatility=0.12,
    )


def setup() -> PortfolioSetup:
    return PortfolioSetup(
        initial_capital=10000, start_date=date(2025, 1, 1), end_date=date(2026, 1, 1),
        strategy="min_variance", max_weight=1, risk_free_rate=0.04,
        weights={}, reference_prices={},
    )


class FakeOptimizationService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict] = []

    def run(self, tickers, start_date, end_date, **kwargs):
        self.calls.append({"tickers": tickers, "start_date": start_date, "end_date": end_date, **kwargs})
        if self.error is not None:
            raise self.error


def test_base_keeps_level_settings_when_cap_is_feasible():
    result = base_recommendation(moderate(), holding_count=3)
    assert (result.strategy, result.max_weight, result.target_volatility) == ("target_risk", 0.35, 0.12)
    assert result.checked is False
    assert result.notes == ["Moderate: Balanced."]


@pytest.mark.parametrize(("count", "cap"), [(2, 0.5), (3, 0.334)])
def test_base_cap_for_few_holdings(count, cap):
    profile = moderate().model_copy(update={"max_weight": 0.25})
    result = base_recommendation(profile, holding_count=count)
    assert result.max_weight == pytest.approx(cap)
    assert count * result.max_weight >= 1
    assert "instead of 25%" in result.notes[-1]


def test_check_success_marks_checked_and_passes_settings():
    service = FakeOptimizationService()
    result = OptimizerRecommendationChecker(service).check(
        base_recommendation(moderate(), 3), TICKERS, setup(),
    )
    assert result.checked is True
    assert result.strategy == "target_risk"
    assert service.calls == [{
        "tickers": TICKERS, "start_date": date(2025, 1, 1), "end_date": date(2026, 1, 1),
        "strategy": "target_risk", "max_weight": 0.35, "risk_free_rate": 0.04,
        "target_volatility": 0.12,
    }]


@pytest.mark.parametrize(
    "error",
    [UnreachableTargetError("Target too low."), NoPositiveExcessReturnError("Nothing beats cash.")],
)
def test_check_falls_back_to_min_variance(error):
    result = OptimizerRecommendationChecker(FakeOptimizationService(error)).check(
        base_recommendation(moderate(), 3), TICKERS, setup(),
    )
    assert result.strategy == "min_variance"
    assert result.target_volatility is None
    assert result.max_weight == 0.35
    assert result.checked is True
    assert error.message in result.notes[-1]
    assert "Minimum variance is recommended instead." in result.notes[-1]


def test_check_keeps_settings_when_optimizer_cannot_run():
    error = InsufficientHistoryError("Choose a longer period.")
    result = OptimizerRecommendationChecker(FakeOptimizationService(error)).check(
        base_recommendation(moderate(), 3), TICKERS, setup(),
    )
    assert result.strategy == "target_risk"
    assert result.checked is False
    assert result.notes[-1] == "Not checked: Choose a longer period."


@pytest.mark.parametrize(("tickers", "portfolio_setup"), [(TICKERS, None), (["AAPL"], setup())])
def test_check_skips_without_setup_or_enough_holdings(tickers, portfolio_setup):
    service = FakeOptimizationService()
    result = OptimizerRecommendationChecker(service).check(
        base_recommendation(moderate(), len(tickers)), tickers, portfolio_setup,
    )
    assert service.calls == []
    assert result.checked is False
    assert result.notes[-1].startswith("Not checked:")
