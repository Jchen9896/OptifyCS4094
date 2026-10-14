"""Exercise the real calculation endpoint with stored-price fixtures."""

from dataclasses import replace
from datetime import date, datetime, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.routes.calculations import get_price_history_reader
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.main import create_app
from app.market_data.base import PriceBar
from app.services.stored_calculation_service import PriceHistoryMetadata, StoredPriceHistory


METADATA = PriceHistoryMetadata(
    source="fixture", retrieved_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
    adjustment_basis="split_dividend_adjusted", interval="1d", exchange="NMS", calendar="XNYS",
)
REQUEST = {"tickers": [" bbb ", "aaa"], "start_date": "2026-10-05", "end_date": "2026-10-07"}


def history(closes, days=(5, 6, 7)):
    return StoredPriceHistory(tuple(
        PriceBar(date(2026, 10, day), close, close, close, close, 0)
        for day, close in zip(days, closes)
    ), METADATA)


class Reader:
    def __init__(self):
        self.batch = {"AAA": history((100, 110, 99)), "BBB": history((100, 120, 108))}
        self.calls = []
        self.error = None

    def read_adjusted_history(self, tickers, start, end):
        self.calls.append((tickers, start, end))
        if self.error:
            raise self.error
        return self.batch


@pytest.fixture
def endpoint():
    app = create_app()
    reader = Reader()
    settings = Settings(_env_file=None, calculation_calendar="XNYS", calculation_annualization_factor=252)
    app.dependency_overrides[get_price_history_reader] = lambda: reader
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client, reader, app


def test_endpoint_returns_labeled_statistics_and_source_metadata(endpoint):
    client, reader, app = endpoint
    response = client.post("/api/calculations", json=REQUEST)
    assert response.status_code == 200
    body = response.json()
    assert body["tickers"] == ["BBB", "AAA"]
    assert body["start_date"] == REQUEST["start_date"]
    assert body["end_date"] == REQUEST["end_date"]
    assert body["intervals"] == [
        {"start_date": "2026-10-05", "end_date": "2026-10-06"},
        {"start_date": "2026-10-06", "end_date": "2026-10-07"},
    ]
    assert body["daily_returns"][0] == pytest.approx([0.2, 0.1])
    assert body["annualized_mean_returns"] == pytest.approx([12.6, 0.0], abs=1e-12)
    assert body["daily_variances"] == pytest.approx([0.045, 0.02])
    assert body["annualized_covariance"] == pytest.approx(np.array([[11.34, 7.56], [7.56, 5.04]]))
    assert body["observation_count"] == 2
    assert body["dropped_interval_count"] == 0
    assert body["warnings"] == []
    assert body["assumptions"]["annualization_factor"] == 252
    assert body["assumptions"]["sample_ddof"] == 1
    assert body["source_metadata"]["AAA"]["source"] == "fixture"
    assert datetime.fromisoformat(body["source_metadata"]["AAA"]["retrieved_at"]) == METADATA.retrieved_at
    assert reader.calls == [(("BBB", "AAA"), date(2026, 10, 5), date(2026, 10, 7))]
    assert "post" in app.openapi()["paths"]["/api/calculations"]


def test_endpoint_uses_configured_annualization(endpoint):
    client, _, app = endpoint
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, calculation_calendar="XNYS", calculation_annualization_factor=100
    )
    body = client.post("/api/calculations", json=REQUEST).json()
    assert body["annualized_mean_returns"] == pytest.approx([5.0, 0.0], abs=1e-12)
    assert body["assumptions"]["annualization_factor"] == 100


def test_dropped_periods_and_undefined_correlation_are_valid_json(endpoint):
    client, reader, _ = endpoint
    reader.batch = {"AAA": history((100, 100, 100, 100), (5, 7, 8, 9)), "BBB": history((100, 200, 100, 110, 99), (5, 6, 7, 8, 9))}
    response = client.post("/api/calculations", json={**REQUEST, "end_date": "2026-10-09"})
    assert response.status_code == 200
    body = response.json()
    assert body["dropped_interval_count"] == 2
    assert body["correlation"] == [[1.0, None], [None, None]]
    assert {warning["code"] for warning in body["warnings"]} == {"dropped_intervals", "undefined_correlation"}


@pytest.mark.parametrize("changes", [
    {"tickers": []}, {"tickers": [" "]}, {"tickers": ["AAA", " aaa "]},
    {"tickers": "AAA"}, {"start_date": "bad-date"}, {"start_date": "2026-10-08"},
    {"start_date": "2026-10-07"},
])
def test_invalid_requests_do_not_read_prices(endpoint, changes):
    client, reader, _ = endpoint
    assert client.post("/api/calculations", json={**REQUEST, **changes}).status_code == 422
    assert reader.calls == []


def test_missing_history_and_invalid_metadata_have_application_errors(endpoint):
    client, reader, _ = endpoint
    reader.batch = {}
    response = client.post("/api/calculations", json=REQUEST)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "insufficient_history"
    reader.batch = {"AAA": history((100, 110, 99)), "BBB": replace(history((100, 120, 108)), metadata=None)}
    response = client.post("/api/calculations", json=REQUEST)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_price_history"


def test_default_reader_reports_unavailable_storage(endpoint):
    client, _, app = endpoint
    del app.dependency_overrides[get_price_history_reader]
    response = client.post("/api/calculations", json=REQUEST)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "price_history_unavailable"


def test_storage_failures_keep_the_existing_error_format(endpoint):
    client, reader, _ = endpoint
    reader.error = AppError("Stored prices are unavailable.", code="price_history_unavailable", status_code=503)
    response = client.post("/api/calculations", json=REQUEST)
    assert response.status_code == 503
    assert response.json() == {"detail": {"code": "price_history_unavailable", "message": "Stored prices are unavailable."}}


def test_unsupported_calendar_period_does_not_read_prices(endpoint):
    client, reader, _ = endpoint
    response = client.post("/api/calculations", json={**REQUEST, "start_date": "2000-01-01"})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unsupported_period"
    assert reader.calls == []
