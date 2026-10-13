"""Unit tests for the market data application error and its HTTP mapping."""

from fastapi.testclient import TestClient

from app.core.errors import AppError, MarketDataUnavailableError
from app.main import create_app


def test_market_data_unavailable_error_has_503_code():
    error = MarketDataUnavailableError()

    assert isinstance(error, AppError)
    assert error.status_code == 503
    assert error.code == "market_data_unavailable"


def test_market_data_unavailable_error_accepts_custom_message():
    assert MarketDataUnavailableError("Provider timed out.").message == "Provider timed out."


def test_app_returns_json_error_for_market_data_error():
    app = create_app()

    @app.get("/test-market-data-down")
    def raise_market_data_down():
        raise MarketDataUnavailableError("Provider timed out.")

    response = TestClient(app).get("/test-market-data-down")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {"code": "market_data_unavailable", "message": "Provider timed out."}
    }
