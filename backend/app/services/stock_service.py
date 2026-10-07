"""Ticker validation service."""

import re

from app.core.config import Settings
from app.core.errors import InvalidTickerFormatError, UnsupportedSecurityError
from app.market_data.base import MarketDataProvider, StockInfo
from app.market_data.yfinance_provider import create_yfinance_provider


class StockService:
    """Confirms that a ticker is a known security of a supported type."""

    def __init__(
        self,
        provider: MarketDataProvider,
        ticker_pattern: str,
        supported_types: list[str],
    ) -> None:
        self._provider = provider
        self._ticker_pattern = re.compile(ticker_pattern)
        self._supported_types = set(supported_types)

    def validate_ticker(self, raw_symbol: str) -> StockInfo:
        """Return the stock for `raw_symbol` only if the provider confirms it.

        Provider errors (`TickerNotFoundError`, `MarketDataUnavailableError`) pass through.
        """
        symbol = raw_symbol.strip().upper()
        # Check the format first, so a bad input does not cause a provider call.
        if not self._ticker_pattern.fullmatch(symbol):
            raise InvalidTickerFormatError(raw_symbol)
        stock = self._provider.get_stock(symbol)
        if stock.quote_type not in self._supported_types:
            raise UnsupportedSecurityError(symbol, stock.quote_type)
        return stock


def create_stock_service(settings: Settings) -> StockService:
    """Make a `StockService` with values from the application settings."""
    return StockService(
        provider=create_yfinance_provider(settings),
        ticker_pattern=settings.ticker_pattern,
        supported_types=settings.supported_security_type_list,
    )
