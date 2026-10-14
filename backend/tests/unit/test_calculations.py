"""Check daily returns with known prices and missing trading sessions."""

from datetime import date

import pytest

from app.core.errors import AppError
from app.market_data.base import PriceBar
from app.services.calculation_service import calculate_daily_returns, calculate_return_summary


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
