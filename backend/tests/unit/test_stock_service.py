"""Unit tests for ticker validation. A fake provider replaces the network."""

import pytest

from app.core.config import Settings
from app.core.errors import (
    InvalidTickerFormatError,
    MarketDataUnavailableError,
    TickerNotFoundError,
    UnsupportedSecurityError,
)
from app.market_data.base import StockInfo
from app.services.stock_service import StockService


class FakeProvider:
    """Acts like a `MarketDataProvider`. It records each symbol and returns one stock or raises a set error."""

    def __init__(self, quote_type="EQUITY", error=None):
        self.stock = StockInfo(symbol="X", name="X", currency=None, exchange=None, quote_type=quote_type)
        self.error = error
        self.symbols = []

    def get_stock(self, symbol):
        self.symbols.append(symbol)
        if self.error:
            raise self.error
        return self.stock


def validate(provider, symbol="AAPL"):
    settings = Settings(supported_security_types=" equity , etf ")
    service = StockService(provider, settings.ticker_pattern, settings.supported_security_type_list)
    return service.validate_ticker(symbol)


@pytest.mark.parametrize("quote_type", ["EQUITY", "ETF"])
def test_supported_security_is_returned(quote_type):
    provider = FakeProvider(quote_type)

    assert validate(provider) == provider.stock


@pytest.mark.parametrize(
    ("raw", "sent"),
    [("  aapl ", "AAPL"), ("BRK-B", "BRK-B"), ("RY.TO", "RY.TO"), ("^GSPC", "^GSPC"), ("EURUSD=X", "EURUSD=X")],
)
def test_symbol_is_cleaned_before_lookup(raw, sent):
    provider = FakeProvider()

    validate(provider, raw)

    assert provider.symbols == [sent]


@pytest.mark.parametrize("symbol", ["", "   ", "AA PL", "AAPL!", "A" * 16])
def test_bad_format_is_rejected_without_provider_call(symbol):
    provider = FakeProvider()

    with pytest.raises(InvalidTickerFormatError):
        validate(provider, symbol)
    assert provider.symbols == []


@pytest.mark.parametrize("quote_type", ["INDEX", "CRYPTOCURRENCY", "MUTUALFUND", None])
def test_unsupported_security_type_is_rejected(quote_type):
    with pytest.raises(UnsupportedSecurityError):
        validate(FakeProvider(quote_type))


@pytest.mark.parametrize("error", [TickerNotFoundError("NOPE"), MarketDataUnavailableError()])
def test_provider_errors_pass_through(error):
    with pytest.raises(type(error)):
        validate(FakeProvider(error=error))


def test_each_failure_has_its_own_code_status_and_message():
    errors = [
        InvalidTickerFormatError("AAPL!"),
        TickerNotFoundError("NOPE"),
        UnsupportedSecurityError("^GSPC", "INDEX"),
        MarketDataUnavailableError(),
    ]

    assert [(error.code, error.status_code) for error in errors] == [
        ("invalid_ticker_format", 422),
        ("ticker_not_found", 404),
        ("unsupported_security", 422),
        ("market_data_unavailable", 503),
    ]
    assert len({error.message for error in errors}) == len(errors)
