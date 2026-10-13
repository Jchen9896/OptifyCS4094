"""Check daily returns with known prices and missing trading sessions."""

from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from app.core.errors import AppError
from app.market_data.base import PriceBar
from app.services.calculation_service import (
    calculate_daily_returns,
    calculate_return_summary,
    calculate_risk_statistics,
)


SESSIONS = [date(2026, 10, day) for day in (5, 6, 7, 8)]


def price(day: date, close: float) -> PriceBar:
    return PriceBar(date=day, open=close, high=close, low=close, close=close, volume=0)


def test_returns_match_hand_calculated_gains_and_losses():
    bars = [price(day, close) for day, close in zip(SESSIONS[:3], (100, 110, 99))]

    result = calculate_daily_returns(bars, SESSIONS[:3])

    assert [item.value for item in result] == pytest.approx([0.10, -0.10])
    assert [(item.start_date, item.end_date) for item in result] == [
        (SESSIONS[0], SESSIONS[1]),
        (SESSIONS[1], SESSIONS[2]),
    ]


def test_price_order_does_not_change_returns_or_modify_input():
    bars = [price(SESSIONS[2], 99), price(SESSIONS[0], 100), price(SESSIONS[1], 110)]
    original = bars.copy()

    result = calculate_daily_returns(bars, SESSIONS[:3])

    assert [item.value for item in result] == pytest.approx([0.10, -0.10])
    assert bars == original


def test_missing_session_removes_both_affected_intervals():
    bars = [price(SESSIONS[0], 100), price(SESSIONS[2], 120), price(SESSIONS[3], 126)]

    result = calculate_daily_returns(bars, SESSIONS)

    assert len(result) == 1
    assert (result[0].start_date, result[0].end_date) == (SESSIONS[2], SESSIONS[3])
    assert result[0].value == pytest.approx(0.05)


@pytest.mark.parametrize(
    "sessions",
    [
        [date(2026, 10, 9), date(2026, 10, 12)],  # Friday to Monday.
        [date(2026, 12, 24), date(2026, 12, 28)],  # Christmas and a weekend.
    ],
)
def test_market_closures_do_not_break_a_daily_return(sessions):
    result = calculate_daily_returns(
        [price(sessions[0], 100), price(sessions[1], 110)], sessions
    )

    assert len(result) == 1
    assert result[0].value == pytest.approx(0.10)


@pytest.mark.parametrize("closes", [[], [100]])
def test_short_history_has_no_returns(closes):
    bars = [price(day, close) for day, close in zip(SESSIONS, closes)]

    assert calculate_daily_returns(bars, SESSIONS) == []


def test_empty_period_has_no_returns():
    assert calculate_daily_returns([], []) == []


def test_constant_prices_have_zero_returns():
    result = calculate_daily_returns([price(day, 100) for day in SESSIONS], SESSIONS)

    assert [item.value for item in result] == [0.0, 0.0, 0.0]


@pytest.mark.parametrize("close", [0, -1, float("nan"), float("inf"), -float("inf")])
def test_invalid_close_is_rejected(close):
    with pytest.raises(AppError, match="finite and greater than zero") as error:
        calculate_daily_returns([price(SESSIONS[0], close)], SESSIONS)

    assert error.value.code == "invalid_price_history"
    assert error.value.status_code == 422


def test_duplicate_price_date_is_rejected():
    with pytest.raises(AppError, match="More than one price"):
        calculate_daily_returns([price(SESSIONS[0], 100), price(SESSIONS[0], 101)], SESSIONS)


@pytest.mark.parametrize("day", [date(2026, 10, 4), date(2026, 10, 9)])
def test_price_outside_expected_sessions_is_rejected(day):
    with pytest.raises(AppError, match="not a trading session"):
        calculate_daily_returns([price(day, 100)], SESSIONS)


@pytest.mark.parametrize("sessions", [SESSIONS[::-1], [SESSIONS[0], SESSIONS[0]]])
def test_invalid_session_order_is_rejected(sessions):
    with pytest.raises(AppError, match="unique and ordered"):
        calculate_daily_returns([], sessions)


def test_return_overflow_is_rejected():
    with pytest.raises(AppError, match="return.*not finite"):
        calculate_daily_returns(
            [price(SESSIONS[0], 1e-300), price(SESSIONS[1], 1e300)], SESSIONS[:2]
        )


def test_summary_preserves_ticker_order_and_has_known_averages():
    histories = {
        "AAA": [price(day, close) for day, close in zip(SESSIONS[:3], (100, 110, 121))],
        "BBB": [price(day, close) for day, close in zip(SESSIONS[:3], (200, 210, 231))],
    }

    result = calculate_return_summary(histories, ["BBB", "AAA"], SESSIONS[:3], 252)

    assert result.tickers == ("BBB", "AAA")
    assert result.intervals == ((SESSIONS[0], SESSIONS[1]), (SESSIONS[1], SESSIONS[2]))
    assert result.daily_returns[0] == pytest.approx((0.05, 0.10))
    assert result.daily_returns[1] == pytest.approx((0.10, 0.10))
    assert result.daily_mean_returns == pytest.approx((0.075, 0.10))
    assert result.annualized_mean_returns == pytest.approx((18.9, 25.2))
    assert result.annualization_factor == 252
    assert result.observation_count == 2
    assert result.dropped_interval_count == 0


def test_shared_periods_determine_each_stocks_average():
    sessions = [date(2026, 10, day) for day in (5, 6, 7, 8, 9)]
    histories = {
        "AAA": [price(day, close) for day, close in zip(sessions, (100, 150, 120, 132, 145.2))],
        "BBB": [price(sessions[0], 100)] + [price(day, 100) for day in sessions[2:]],
    }

    result = calculate_return_summary(histories, ["AAA", "BBB"], sessions, 252)

    assert result.intervals == ((sessions[2], sessions[3]), (sessions[3], sessions[4]))
    assert result.daily_mean_returns == pytest.approx((0.10, 0.0))
    assert result.annualized_mean_returns == pytest.approx((25.2, 0.0))
    assert result.observation_count == 2
    assert result.dropped_interval_count == 2


def test_single_stock_summary_accepts_custom_annualization_and_unsorted_prices():
    bars = [price(SESSIONS[2], 121), price(SESSIONS[0], 100), price(SESSIONS[1], 110)]
    original = bars.copy()

    result = calculate_return_summary({"AAA": bars}, ["AAA"], SESSIONS[:3], 100)

    assert result.daily_mean_returns == pytest.approx((0.10,))
    assert result.annualized_mean_returns == pytest.approx((10.0,))
    assert result.annualization_factor == 100
    assert bars == original


def test_constant_prices_have_zero_average_returns():
    result = calculate_return_summary(
        {"AAA": [price(day, 100) for day in SESSIONS]}, ["AAA"], SESSIONS, 252
    )

    assert result.daily_mean_returns == (0.0,)
    assert result.annualized_mean_returns == (0.0,)


@pytest.mark.parametrize("tickers", [[], [""], [" "], ["AAA", "AAA"]])
def test_summary_rejects_empty_or_duplicate_tickers(tickers):
    with pytest.raises(AppError) as error:
        calculate_return_summary({}, tickers, SESSIONS, 252)

    assert error.value.code == "invalid_calculation_input"
    assert error.value.status_code == 422


@pytest.mark.parametrize("factor", [0, -1, float("nan"), float("inf")])
def test_summary_rejects_invalid_annualization_factor(factor):
    with pytest.raises(AppError, match="annualization factor") as error:
        calculate_return_summary({}, ["AAA"], SESSIONS, factor)

    assert error.value.code == "invalid_calculation_input"


@pytest.mark.parametrize(
    "histories",
    [
        {},
        {"AAA": []},
        {"AAA": [price(SESSIONS[0], 100), price(SESSIONS[1], 110)]},
        {
            "AAA": [price(SESSIONS[0], 100), price(SESSIONS[1], 110)],
            "BBB": [price(SESSIONS[2], 100), price(SESSIONS[3], 110)],
        },
        {
            "AAA": [price(day, 100) for day in SESSIONS],
            "BBB": [price(SESSIONS[0], 100), price(SESSIONS[2], 100), price(SESSIONS[3], 100)],
        },
    ],
)
def test_summary_rejects_missing_or_insufficient_shared_history(histories):
    with pytest.raises(AppError) as error:
        calculate_return_summary(histories, list(histories) or ["AAA"], SESSIONS, 252)

    assert error.value.code == "insufficient_history"
    assert error.value.status_code == 422


def test_summary_checks_prices_for_every_selected_stock():
    histories = {
        "AAA": [price(day, 100) for day in SESSIONS],
        "BBB": [price(day, close) for day, close in zip(SESSIONS, (100, 0, 100, 100))],
    }

    with pytest.raises(AppError, match="finite and greater than zero"):
        calculate_return_summary(histories, ["AAA", "BBB"], SESSIONS, 252)


def test_summary_rejects_annualized_return_overflow():
    histories = {"AAA": [price(day, close) for day, close in zip(SESSIONS[:3], (1, 1000, 1000000))]}

    with pytest.raises(AppError, match="non-finite average returns") as error:
        calculate_return_summary(histories, ["AAA"], SESSIONS[:3], 1e308)

    assert error.value.code == "invalid_calculation_result"


def summary_for_prices(closes_by_ticker, tickers=None, factor=252):
    sessions = [date(2026, 10, day) for day in (5, 6, 7, 8, 9)]
    histories = {
        ticker: [price(day, close) for day, close in zip(sessions, closes)]
        for ticker, closes in closes_by_ticker.items()
    }
    sessions = sessions[:max(len(closes) for closes in closes_by_ticker.values())]
    return calculate_return_summary(histories, tickers or list(histories), sessions, factor)


def test_risk_matches_hand_calculated_opposite_returns():
    summary = summary_for_prices({"AAA": [100, 110, 99], "BBB": [100, 90, 99]})

    result = calculate_risk_statistics(summary)

    assert result.tickers == ("AAA", "BBB")
    assert result.daily_variances == pytest.approx((0.02, 0.02), abs=1e-12)
    assert result.daily_covariance == pytest.approx(np.array([[0.02, -0.02], [-0.02, 0.02]]))
    assert result.annualized_variances == pytest.approx((5.04, 5.04), abs=1e-12)
    assert result.annualized_covariance == pytest.approx(np.array([[5.04, -5.04], [-5.04, 5.04]]))
    assert result.correlation == pytest.approx(np.array([[1, -1], [-1, 1]]), abs=1e-12)
    assert result.warnings == ()


def test_risk_preserves_ticker_order_and_positive_relationship():
    summary = summary_for_prices({"AAA": [100, 110, 99], "BBB": [200, 240, 192]}, ["BBB", "AAA"])

    result = calculate_risk_statistics(summary)

    assert result.tickers == ("BBB", "AAA")
    assert result.daily_variances == pytest.approx((0.08, 0.02), abs=1e-12)
    assert result.daily_covariance == pytest.approx(np.array([[0.08, 0.04], [0.04, 0.02]]))
    assert result.correlation == pytest.approx(np.ones((2, 2)), abs=1e-12)


def test_uncorrelated_returns_have_zero_covariance():
    result = calculate_risk_statistics(summary_for_prices({
        "AAA": [100, 125, 93.75, 117.1875, 87.890625],
        "BBB": [100, 125, 156.25, 117.1875, 87.890625],
    }))

    assert result.daily_covariance[0][1] == pytest.approx(0.0, abs=1e-12)
    assert result.correlation == ((1.0, 0.0), (0.0, 1.0))


def test_single_stock_risk_keeps_one_by_one_matrices():
    result = calculate_risk_statistics(summary_for_prices({"AAA": [100, 110, 99]}, factor=100))

    assert result.daily_covariance == pytest.approx(np.array([[0.02]]))
    assert result.annualized_variances == pytest.approx((2.0,))
    assert result.annualized_covariance == pytest.approx(np.array([[2.0]]))
    assert result.correlation == ((1.0,),)


@pytest.mark.parametrize("constant_prices", [[100, 100, 100], [100, 125, 156.25]])
def test_zero_variance_has_null_correlations_and_a_warning(constant_prices):
    result = calculate_risk_statistics(
        summary_for_prices({"AAA": constant_prices, "BBB": [100, 110, 99]})
    )

    assert result.daily_variances == pytest.approx((0.0, 0.02))
    assert result.daily_covariance[0] == (0.0, 0.0)
    assert result.correlation == ((None, None), (None, 1.0))
    assert len(result.warnings) == 1
    assert result.warnings[0].code == "undefined_correlation"
    assert result.warnings[0].tickers == ("AAA",)


def test_all_constant_stocks_have_zero_risk_and_no_defined_correlation():
    result = calculate_risk_statistics(summary_for_prices({"AAA": [100, 100, 100], "BBB": [50, 50, 50]}))

    assert result.daily_covariance == ((0.0, 0.0), (0.0, 0.0))
    assert result.annualized_covariance == ((0.0, 0.0), (0.0, 0.0))
    assert result.correlation == ((None, None), (None, None))
    assert [warning.tickers for warning in result.warnings] == [("AAA",), ("BBB",)]


def test_risk_uses_only_shared_periods_after_a_missing_price():
    summary = summary_for_prices({"AAA": [100, 200, 100, 110, 99], "BBB": [100, 100, 100, 110, 99]})
    sessions = [date(2026, 10, day) for day in (5, 6, 7, 8, 9)]
    histories = {
        "AAA": [price(day, close) for day, close in zip(sessions, (100, 200, 100, 110, 99))],
        "BBB": [price(sessions[0], 100), price(sessions[2], 100), price(sessions[3], 110), price(sessions[4], 99)],
    }
    shared = calculate_return_summary(histories, ["AAA", "BBB"], sessions, 252)

    result = calculate_risk_statistics(shared)

    assert shared.observation_count == 2
    assert result.daily_variances == pytest.approx((0.02, 0.02), abs=1e-12)
    assert result.correlation == pytest.approx(np.ones((2, 2)), abs=1e-12)
    assert calculate_risk_statistics(summary).daily_variances[0] > result.daily_variances[0]


def test_risk_matrices_are_symmetric_and_variances_match_the_diagonal():
    result = calculate_risk_statistics(
        summary_for_prices({"AAA": [100, 102, 99, 104, 103], "BBB": [100, 98, 100, 99, 101], "CCC": [50, 55, 52, 53, 56]})
    )

    covariance = np.asarray(result.daily_covariance)
    correlation = np.asarray(result.correlation)
    assert covariance == pytest.approx(covariance.T, abs=1e-12)
    assert correlation == pytest.approx(correlation.T, abs=1e-12)
    assert np.diag(covariance) == pytest.approx(result.daily_variances, abs=1e-12)
    assert np.diag(correlation) == pytest.approx(np.ones(3), abs=1e-12)
    assert np.abs(correlation).max() <= 1
    assert np.linalg.eigvalsh(covariance).min() >= -1e-12
    assert np.asarray(result.annualized_covariance) == pytest.approx(covariance * 252)


@pytest.mark.parametrize("prices,factor", [([1e-200, 1, 1], 252), ([1, 4, 1], 1e308)])
def test_non_finite_risk_is_rejected(prices, factor):
    summary = summary_for_prices({"AAA": prices}, factor=factor)

    with pytest.raises(AppError, match="non-finite risk") as error:
        calculate_risk_statistics(summary)

    assert error.value.code == "invalid_calculation_result"


@pytest.mark.parametrize("changes", [
    {"daily_returns": ((0.1,), (0.1, 0.2))},
    {"daily_returns": ((float("nan"),), (0.1,))},
    {"annualization_factor": 0},
])
def test_risk_rejects_invalid_return_summaries(changes):
    summary = replace(summary_for_prices({"AAA": [100, 110, 99]}), **changes)

    with pytest.raises(AppError) as error:
        calculate_risk_statistics(summary)

    assert error.value.code == "invalid_calculation_input"


def test_risk_requires_at_least_two_shared_periods():
    summary = summary_for_prices({"AAA": [100, 110, 99]})
    summary = replace(summary, intervals=summary.intervals[:1], daily_returns=summary.daily_returns[:1])

    with pytest.raises(AppError) as error:
        calculate_risk_statistics(summary)

    assert error.value.code == "insufficient_history"
