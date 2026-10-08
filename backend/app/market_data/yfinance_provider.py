"""Market data provider that uses the yfinance library."""

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import yfinance

from app.core.config import Settings
from app.core.errors import MarketDataUnavailableError, TickerNotFoundError
from app.market_data.base import MarketDataProvider, PriceBar, StockInfo
from app.market_data.normalizers import (
    QUOTE_TYPE_KEY,
    normalize_price_frame,
    normalize_search_quote,
    normalize_stock_info,
)


class YFinanceProvider(MarketDataProvider):
    """Gets stock data from Yahoo Finance through yfinance.

    `ticker_factory` makes a ticker object for a symbol. The default is
    `yfinance.Ticker`. `search_factory` runs a search. The default is
    `yfinance.Search`. Tests give fake factories, so they do not use the network.
    """

    def __init__(
        self,
        interval: str,
        auto_adjust: bool,
        search_limit: int,
        ticker_factory: Callable[[str], Any] = yfinance.Ticker,
        search_factory: Callable[..., Any] = yfinance.Search,
    ) -> None:
        self._interval = interval
        self._auto_adjust = auto_adjust
        self._search_limit = search_limit
        self._ticker_factory = ticker_factory
        self._search_factory = search_factory

    def get_stock(self, symbol: str) -> StockInfo:
        try:
            info = self._ticker_factory(symbol).info
        # yfinance does not have one stable error type. Network, rate limit, and
        # data errors come from different libraries. Thus we catch all errors here,
        # at the provider boundary only, and change them to one application error.
        except Exception as error:
            raise MarketDataUnavailableError() from error
        info = info or {}
        # yfinance does not raise an error for an unknown symbol. It returns
        # data with no quote type. A known security always has a quote type.
        if not info.get(QUOTE_TYPE_KEY):
            raise TickerNotFoundError(symbol)
        return normalize_stock_info(symbol, info)

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

    def search_stocks(self, query: str) -> list[StockInfo]:
        try:
            search = self._search_factory(
                query,
                max_results=self._search_limit,
                # Get only stock results. Do not get news, lists, or private companies.
                news_count=0,
                lists_count=0,
                include_cb=False,
                recommended=0,
            )
        # See the comment in `get_stock` about why all errors are caught.
        except Exception as error:
            raise MarketDataUnavailableError() from error
        # When Yahoo sends a bad answer, yfinance gives an empty response. An answer
        # with no match still has data. Thus only an empty response is a provider error.
        if not search.response:
            raise MarketDataUnavailableError()
        return [normalize_search_quote(quote) for quote in search.quotes]


def create_yfinance_provider(settings: Settings) -> YFinanceProvider:
    """Make a `YFinanceProvider` with values from the application settings."""
    return YFinanceProvider(
        interval=settings.market_data_interval,
        auto_adjust=settings.market_data_auto_adjust,
        search_limit=settings.market_data_search_limit,
    )
