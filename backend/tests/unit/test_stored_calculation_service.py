"""Test saved-history integration without a database or external provider."""

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from app.core.errors import AppError
from app.market_data.base import PriceBar
from app.services.optimization_input_service import prepare_optimization
from app.services.stored_calculation_service import (
    PriceHistoryMetadata,
    StoredCalculationService,
    StoredPriceHistory,
)


SESSIONS = tuple(date(2026, 10, day) for day in (5, 6, 7))
METADATA = PriceHistoryMetadata(
    source="fixture", retrieved_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
    adjustment_basis="split_dividend_adjusted", interval="1d", exchange="NMS", calendar="XNYS",
)


def history(closes=(100, 110, 99), sessions=SESSIONS, metadata=METADATA):
    prices = tuple(PriceBar(day, close, close, close, close, 0) for day, close in zip(sessions, closes))
    return StoredPriceHistory(prices=prices, metadata=metadata)


class FakeReader:
    def __init__(self, batch=None, error=None):
        self.batch = batch if batch is not None else {"AAA": history(), "BBB": history((100, 120, 108))}
        self.error = error
        self.calls = []

    def read_adjusted_history(self, tickers, start_date, end_date):
        self.calls.append((tickers, start_date, end_date))
        if self.error:
            raise self.error
        return self.batch


class FakeCalendar:
    name = "XNYS"

    def __init__(self, sessions=SESSIONS):
        self.sessions = sessions

    def sessions_in_range(self, _start, _end):
        return self.sessions


def service(reader=None, sessions=SESSIONS, factor=252):
    return StoredCalculationService(reader or FakeReader(), FakeCalendar(sessions), factor)


def test_reads_one_batch_and_passes_annual_statistics_to_the_optimizer():
    reader = FakeReader()

    result = service(reader).calculate([" bbb ", "aaa"], SESSIONS[0], SESSIONS[-1])
    prepared = prepare_optimization(
        result.returns, period_start=result.period_start, period_end=result.period_end,
        strategy="min_variance", tolerance=1e-8,
    )

    assert reader.calls == [(("BBB", "AAA"), SESSIONS[0], SESSIONS[-1])]
    assert result.returns.tickers == result.risk.tickers == ("BBB", "AAA")
    assert prepared.optimizer_input.expected_returns == pytest.approx([12.6, 0.0], abs=1e-12)
    assert prepared.optimizer_input.covariance[0] == pytest.approx([11.34, 7.56])
    assert result.source_metadata == {"BBB": METADATA, "AAA": METADATA}
    assert result.calendar == "XNYS"
    assert result.warnings == ()


def test_missing_prices_produce_shared_intervals_and_readable_warnings():
    sessions = tuple(date(2026, 10, day) for day in (5, 6, 7, 8, 9))
    reader = FakeReader({
        "AAA": history((100, 200, 100, 110, 99), sessions),
        "BBB": history((100, 100, 100, 100), (sessions[0], *sessions[2:])),
    })

    result = service(reader, sessions).calculate(["AAA", "BBB"], sessions[0], sessions[-1])

    assert result.returns.intervals == ((sessions[2], sessions[3]), (sessions[3], sessions[4]))
    assert result.returns.dropped_interval_count == 2
    assert result.risk.daily_variances == pytest.approx((0.02, 0.0))
    assert {warning.code for warning in result.warnings} == {"undefined_correlation", "dropped_intervals"}


def test_single_stock_service_uses_the_supplied_annualization_factor():
    result = service(FakeReader({"AAA": history((100, 110, 121))}), factor=100).calculate(
        ["AAA"], SESSIONS[0], SESSIONS[-1]
    )

    assert result.returns.tickers == ("AAA",)
    assert result.returns.annualized_mean_returns == pytest.approx((10.0,))
    assert result.returns.annualization_factor == 100


@pytest.mark.parametrize("metadata", [
    None, replace(METADATA, source=None), replace(METADATA, source=" "),
    replace(METADATA, retrieved_at=None), replace(METADATA, retrieved_at=datetime(2026, 10, 8)),
    replace(METADATA, adjustment_basis="raw"), replace(METADATA, adjustment_basis=None),
    replace(METADATA, interval="1wk"), replace(METADATA, interval=None),
    replace(METADATA, exchange=None), replace(METADATA, exchange=" "),
    replace(METADATA, calendar=None), replace(METADATA, calendar="XLON"),
])
def test_missing_or_incompatible_saved_metadata_is_rejected(metadata):
    reader = FakeReader({"AAA": history(metadata=metadata)})

    with pytest.raises(AppError) as error:
        service(reader).calculate(["AAA"], SESSIONS[0], SESSIONS[-1])

    assert error.value.code == "invalid_price_history"
    assert error.value.status_code == 422


@pytest.mark.parametrize("tickers,start,end", [
    ([], SESSIONS[0], SESSIONS[-1]), ([" "], SESSIONS[0], SESSIONS[-1]),
    (["AAA", " aaa "], SESSIONS[0], SESSIONS[-1]),
    (["AAA"], SESSIONS[-1], SESSIONS[0]), (["AAA"], SESSIONS[0], SESSIONS[0]),
])
def test_invalid_requests_do_not_read_storage(tickers, start, end):
    reader = FakeReader()
    with pytest.raises(AppError) as error:
        service(reader).calculate(tickers, start, end)

    assert error.value.code == "invalid_calculation_input"
    assert reader.calls == []


@pytest.mark.parametrize("sessions,code", [
    ((), "insufficient_history"), (SESSIONS[:2], "insufficient_history"),
    (SESSIONS[::-1], "invalid_price_history"), ((SESSIONS[0],) * 3, "invalid_price_history"),
    ((date(2026, 10, 4), *SESSIONS), "invalid_price_history"),
])
def test_invalid_calendar_output_does_not_read_storage(sessions, code):
    reader = FakeReader()
    with pytest.raises(AppError) as error:
        service(reader, sessions).calculate(["AAA"], SESSIONS[0], SESSIONS[-1])

    assert error.value.code == code
    assert reader.calls == []


def test_empty_storage_is_distinct_from_a_storage_failure():
    with pytest.raises(AppError) as missing:
        service(FakeReader({})).calculate(["AAA"], SESSIONS[0], SESSIONS[-1])
    assert missing.value.code == "insufficient_history"
    assert missing.value.status_code == 422

    failure = AppError("Storage is unavailable.", code="price_history_unavailable", status_code=503)
    with pytest.raises(AppError) as unavailable:
        service(FakeReader(error=failure)).calculate(["AAA"], SESSIONS[0], SESSIONS[-1])
    assert unavailable.value is failure


@pytest.mark.parametrize("factor", [0, -1, float("nan"), float("inf")])
def test_invalid_configuration_is_rejected(factor):
    with pytest.raises(AppError, match="annualization factor"):
        service(factor=factor)
