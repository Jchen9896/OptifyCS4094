"""API tests for stock search. A fake service replaces the provider."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes.stocks import get_stock_service
from app.core.errors import InvalidSearchQueryError, MarketDataUnavailableError
from app.main import create_app
from app.market_data.base import StockInfo


class FakeStockService:
    def __init__(self, results=(), error=None):
        self.results = list(results)
        self.error = error

    def search_stocks(self, _query):
        if self.error:
            raise self.error
        return self.results


def search(path, service):
    app = create_app()
    app.dependency_overrides[get_stock_service] = lambda: service
    return TestClient(app).get(path)


APPLE = StockInfo(symbol="AAPL", name="Apple Inc.", currency=None, exchange="NMS", quote_type="EQUITY")
APPLE_JSON = {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NMS", "quote_type": "EQUITY"}


# A match shows the ticker and company name. No match is a success with an empty list.
@pytest.mark.parametrize(("results", "expected"), [([APPLE], [APPLE_JSON]), ([], [])])
def test_search_returns_results(results, expected):
    response = search("/api/stocks?q=apple", FakeStockService(results))

    assert response.status_code == 200
    assert response.json() == {"query": "apple", "results": expected}


@pytest.mark.parametrize(
    ("error", "status_code"),
    [(InvalidSearchQueryError(), 422), (MarketDataUnavailableError(), 503)],
)
def test_search_failure_has_its_own_code_and_message(error, status_code):
    response = search("/api/stocks", FakeStockService(error=error))

    assert response.status_code == status_code
    assert response.json() == {"detail": {"code": error.code, "message": error.message}}
