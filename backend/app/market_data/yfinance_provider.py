"""Market data provider that uses the yfinance library."""

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import yfinance

from app.core.config import Settings
from app.core.errors import MarketDataUnavailableError
from app.market_data.base import MarketDataProvider, PriceBar, StockInfo
from app.market_data.normalizers import normalize_price_frame, normalize_stock_info


class YFinanceProvider(MarketDataProvider):
    """Gets stock data from Yahoo Finance through yfinance.

    `ticker_factory` makes a ticker object for a symbol. The default is
    `yfinance.Ticker`. Tests give a fake factory, so they do not use the network.
    """

    def __init__(
        self,
        interval: str,
        auto_adjust: bool,
        ticker_factory: Callable[[str], Any] = yfinance.Ticker,
    ) -> None:
        self._interval = interval
        self._auto_adjust = auto_adjust
        self._ticker_factory = ticker_factory

    def get_stock(self, symbol: str) -> StockInfo:
        try:
            info = self._ticker_factory(symbol).info
        # yfinance does not have one stable error type. Network, rate limit, and
        # data errors come from different libraries. Thus we catch all errors here,
        # at the provider boundary only, and change them to one application error.
        except Exception as error:
            raise MarketDataUnavailableError() from error
        return normalize_stock_info(symbol, info or {})

    def get_price_history(self, symbol: str, start: date, end: date) -> list[PriceBar]:
        try:
            frame = self._ticker_factory(symbol).history(
                start=start,
                # yfinance does not include the end date. Add one day to include it.
                end=end + timedelta(days=1),
                interval=self._interval,
                auto_adjust=self._auto_adjust,
            )
        # See the comment in `get_stock` about why all errors are caught.
        except Exception as error:
            raise MarketDataUnavailableError() from error
        if frame.empty:
            return []
        return normalize_price_frame(frame)


def create_yfinance_provider(settings: Settings) -> YFinanceProvider:
    """Make a `YFinanceProvider` with values from the application settings."""
    return YFinanceProvider(
        interval=settings.market_data_interval,
        auto_adjust=settings.market_data_auto_adjust,
    )
