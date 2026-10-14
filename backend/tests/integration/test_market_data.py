"""API tests for historical price retrieval. A fake service replaces the DB and provider."""

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes.market_data import get_market_data_service
from app.core.errors import InsufficientHistoryError, InvalidDateRangeError, MarketDataUnavailableError
from app.main import create_app
from app.services.market_data_service import PriceHistoryResult


class FakeMarketDataService:
    def __init__(self, result: PriceHistoryResult | None = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls: list[tuple[str, date, date]] = []

    def get_or_fetch_history(self, symbol: str, start: date, end: date) -> PriceHistoryResult:
        self.calls.append((symbol, start, end))
        if self.error:
            raise self.error
        assert self.result is not None
        return self.result


SUCCESS = PriceHistoryResult(
    symbol="AAPL",
    start_date=date(2026, 1, 2),
    end_date=date(2026, 1, 5),
    bar_count=2,
    first_date=date(2026, 1, 2),
    last_date=date(2026, 1, 5),
    last_close=150.25,
    source="yfinance",
    fetched_at=datetime(2026, 10, 14, tzinfo=timezone.utc),
    served_from_database=False,
)


def post_history(service: FakeMarketDataService, body: dict):
    app = create_app()
    app.dependency_overrides[get_market_data_service] = lambda: service
    return TestClient(app).post("/api/market-data/history", json=body)


def test_history_returns_stored_summary():
    response = post_history(
        FakeMarketDataService(SUCCESS),
        {"symbol": "AAPL", "start_date": "2026-01-02", "end_date": "2026-01-05"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["bar_count"] == 2
    assert payload["last_close"] == 150.25
    assert payload["served_from_database"] is False
    assert payload["source"] == "yfinance"


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (InvalidDateRangeError(), 422),
        (InsufficientHistoryError(), 422),
        (MarketDataUnavailableError(), 503),
    ],
)
def test_history_failure_has_its_own_code_and_message(error, status_code):
    response = post_history(
        FakeMarketDataService(error=error),
        {"symbol": "AAPL", "start_date": "2026-01-02", "end_date": "2026-01-05"},
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": {"code": error.code, "message": error.message}}
