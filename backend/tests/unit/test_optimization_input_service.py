"""Check the handoff from calculated statistics to the actual optimizer schema."""

from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from app.core.errors import InvalidOptimizationInputError
from app.market_data.base import PriceBar
from app.schemas.optimization import OptimizerInput
from app.services.calculation_service import calculate_return_summary
from app.services.optimization_input_service import prepare_optimization


SESSIONS = [date(2026, 10, day) for day in (5, 6, 7)]


def summary(tickers=("BBB", "AAA"), factor=252):
    histories = {
        ticker: [PriceBar(day, close, close, close, close, 0) for day, close in zip(SESSIONS, closes)]
        for ticker, closes in {"AAA": (100, 110, 99), "BBB": (100, 120, 108)}.items()
    }
    return calculate_return_summary(histories, tickers, SESSIONS, factor)


def prepare(calculated=None, **changes):
    options = {
        "period_start": date(2026, 10, 1),
        "period_end": date(2026, 10, 9),
        "strategy": "min_variance",
        "tolerance": 1e-8,
    }
    options.update(changes)
    return prepare_optimization(calculated or summary(), **options)


def test_handoff_uses_annual_statistics_in_ticker_order():
    result = prepare(max_weight=0.8, risk_free_rate=0.03)
    data = result.optimizer_input

    assert isinstance(data, OptimizerInput)
    assert data.tickers == ["BBB", "AAA"]
    assert data.expected_returns == pytest.approx([12.6, 0.0], abs=1e-12)
    assert data.covariance == pytest.approx(np.array([[11.34, 7.56], [7.56, 5.04]]), abs=1e-12)
    assert data.period_start == date(2026, 10, 1)
    assert data.period_end == date(2026, 10, 9)
    assert data.strategy == "min_variance"
    assert data.max_weight == 0.8
    assert data.risk_free_rate == 0.03
    assert any("252 trading sessions" in item for item in result.assumptions)
    assert any("without compounding" in item for item in result.assumptions)
    assert any("0.03" in item for item in result.assumptions)


def test_handoff_uses_the_summarys_custom_annualization_factor():
    result = prepare(summary(factor=100))

    assert result.optimizer_input.expected_returns == pytest.approx([5.0, 0.0], abs=1e-12)
    assert result.optimizer_input.covariance == pytest.approx(np.array([[4.5, 3.0], [3.0, 2.0]]))
    assert any("100 trading sessions" in item for item in result.assumptions)
    assert result.optimizer_input.max_weight is None
    assert result.optimizer_input.risk_free_rate is None


def test_single_stock_analysis_is_not_sent_to_the_optimizer():
    calculated = summary(tickers=("AAA",))

    assert calculated.observation_count == 2
    with pytest.raises(InvalidOptimizationInputError, match="at least two stocks"):
        prepare(calculated)


@pytest.mark.parametrize("changes", [
    {"period_start": date(2026, 10, 9)},
    {"period_end": date(2026, 9, 30)},
    {"period_start": date(2026, 10, 6)},
    {"period_end": date(2026, 10, 6)},
    {"strategy": " "},
    {"tolerance": -1},
    {"tolerance": float("nan")},
    {"tolerance": float("inf")},
    {"risk_free_rate": float("nan")},
    {"risk_free_rate": float("inf")},
    {"max_weight": 0},
    {"max_weight": 1.5},
])
def test_invalid_optimizer_options_use_the_application_error(changes):
    with pytest.raises(InvalidOptimizationInputError) as error:
        prepare(**changes)

    assert error.value.code == "invalid_optimization_input"
    assert error.value.status_code == 422


@pytest.mark.parametrize("changes,message", [
    ({"tickers": ("AAA", "AAA")}, "more than once"),
    ({"annualized_mean_returns": (0.1,)}, "expected returns"),
    ({"annualized_mean_returns": (float("nan"), 0.1)}, "missing or infinite"),
])
def test_existing_optimizer_validation_checks_the_prepared_input(changes, message):
    calculated = replace(summary(), **changes)

    with pytest.raises(InvalidOptimizationInputError, match=message):
        prepare(calculated)
