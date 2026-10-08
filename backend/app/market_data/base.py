"""Market data provider interface and internal data types.

Application code uses only these types. It does not use the raw data
from a provider. This lets us change the data source without changes
to portfolio logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class StockInfo:
    """Basic data about one stock."""

    symbol: str
    name: str
    currency: str | None
    exchange: str | None
    quote_type: str | None


@dataclass(frozen=True)
class PriceBar:
    """Prices for one stock on one trading day."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketDataProvider(ABC):
    """Gets stock data from an external source.

    Implementations must return only the internal types above. When the
    source fails, they must raise `MarketDataUnavailableError` from
    `app.core.errors`. They must not let provider-specific errors through.
    """

    @abstractmethod
    def get_stock(self, symbol: str) -> StockInfo:
        """Return basic data for `symbol`.

        Raise `TickerNotFoundError` if the source does not know `symbol`.
        """

    @abstractmethod
    def get_price_history(self, symbol: str, start: date, end: date) -> list[PriceBar]:
        """Return daily prices for `symbol` from `start` to `end`, oldest first."""

    @abstractmethod
    def search_stocks(self, query: str) -> list[StockInfo]:
        """Return stocks whose ticker or company name matches `query`, best match first.

        Return an empty list if no stock matches.
        """
