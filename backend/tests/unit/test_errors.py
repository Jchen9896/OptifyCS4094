"""Unit tests for the market data application error and its HTTP mapping."""

import pytest
from fastapi.testclient import TestClient

from app.core.errors import (
    AppError,
    InsufficientHistoryError,
    InvalidDateRangeError,
    MarketDataUnavailableError,
    UnreliablePriceHistoryError,
)
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


@pytest.mark.parametrize(
    ("error", "code", "status_code"),
    [
        (InvalidDateRangeError(), "invalid_date_range", 422),
        (UnreliablePriceHistoryError(), "unreliable_price_history", 422),
        (InsufficientHistoryError(), "insufficient_history", 422),
    ],
)
def test_history_errors_have_expected_codes(error: AppError, code: str, status_code: int):
    assert isinstance(error, AppError)
    assert error.code == code
    assert error.status_code == status_code


def test_invalid_date_range_error_accepts_custom_message():
    assert InvalidDateRangeError("The range is too long.").message == "The range is too long."


def test_app_returns_json_error_for_invalid_date_range():
    app = create_app()

    @app.get("/test-invalid-date-range")
    def raise_invalid_date_range():
        raise InvalidDateRangeError("The range is too long.")

    response = TestClient(app).get("/test-invalid-date-range")

    assert response.status_code == 422
    assert response.json() == {
        "detail": {"code": "invalid_date_range", "message": "The range is too long."}
    }
