"""Unit tests for the yfinance provider. A fake ticker replaces the network."""

from datetime import date

import pandas as pd
import pytest

from app.core.config import Settings
from app.core.errors import MarketDataUnavailableError, TickerNotFoundError
from app.market_data.base import MarketDataProvider, PriceBar, StockInfo
from app.market_data.yfinance_provider import YFinanceProvider, create_yfinance_provider


class FakeTicker:
    """Acts like `yfinance.Ticker`. It returns set data or raises a set error."""

    def __init__(self, info=None, frame=None, error=None):
        self._info = info
        self._frame = frame
        self._error = error
        self.history_kwargs = None

    @property
    def info(self):
        if self._error:
            raise self._error
        return self._info

    def history(self, **kwargs):
        self.history_kwargs = kwargs
        if self._error:
            raise self._error
        return self._frame


def make_provider(ticker: FakeTicker) -> YFinanceProvider:
    return YFinanceProvider(interval="1d", auto_adjust=True, ticker_factory=lambda _symbol: ticker)


def test_provider_implements_interface():
    assert isinstance(make_provider(FakeTicker()), MarketDataProvider)


def test_get_stock_returns_internal_format():
    ticker = FakeTicker(
        info={"longName": "Apple Inc.", "currency": "USD", "exchange": "NMS", "quoteType": "EQUITY"}
    )

    assert make_provider(ticker).get_stock("AAPL") == StockInfo(
        symbol="AAPL", name="Apple Inc.", currency="USD", exchange="NMS", quote_type="EQUITY"
    )


def test_get_stock_with_no_name_uses_symbol():
    assert make_provider(FakeTicker(info={"quoteType": "ETF"})).get_stock("SPY").name == "SPY"


# yfinance 0.2.61 returns empty or near-empty info for an unknown symbol.
@pytest.mark.parametrize("info", [None, {}, {"trailingPegRatio": None}])
def test_get_stock_with_no_quote_type_raises_ticker_not_found(info):
    with pytest.raises(TickerNotFoundError) as raised:
        make_provider(FakeTicker(info=info)).get_stock("NOPE")

    assert raised.value.code == "ticker_not_found"
    assert raised.value.status_code == 404
    assert "NOPE" in raised.value.message


def test_get_price_history_returns_internal_format():
    frame = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [100]},
        index=pd.DatetimeIndex(["2026-01-02"]),
    )

    bars = make_provider(FakeTicker(frame=frame)).get_price_history("AAPL", date(2026, 1, 1), date(2026, 1, 31))

    assert bars == [PriceBar(date=date(2026, 1, 2), open=1.0, high=2.0, low=0.5, close=1.5, volume=100)]


def test_get_price_history_sends_settings_and_includes_end_date():
    ticker = FakeTicker(frame=pd.DataFrame())
    provider = YFinanceProvider(interval="1wk", auto_adjust=False, ticker_factory=lambda _symbol: ticker)

    provider.get_price_history("AAPL", date(2026, 1, 1), date(2026, 1, 31))

    assert ticker.history_kwargs == {
        "start": date(2026, 1, 1),
        "end": date(2026, 2, 1),
        "interval": "1wk",
        "auto_adjust": False,
    }


def test_get_price_history_with_empty_frame_returns_empty_list():
    assert make_provider(FakeTicker(frame=pd.DataFrame())).get_price_history(
        "AAPL", date(2026, 1, 1), date(2026, 1, 31)
    ) == []


@pytest.mark.parametrize("error", [ConnectionError("down"), ValueError("bad data"), KeyError("x")])
def test_provider_errors_become_application_error(error):
    provider = make_provider(FakeTicker(error=error))

    with pytest.raises(MarketDataUnavailableError) as raised:
        provider.get_stock("AAPL")
    assert raised.value.__cause__ is error

    with pytest.raises(MarketDataUnavailableError):
        provider.get_price_history("AAPL", date(2026, 1, 1), date(2026, 1, 31))


def test_create_yfinance_provider_uses_settings():
    ticker = FakeTicker(frame=pd.DataFrame())
    provider = create_yfinance_provider(Settings(market_data_interval="1mo", market_data_auto_adjust=False))
    provider._ticker_factory = lambda _symbol: ticker

    provider.get_price_history("AAPL", date(2026, 1, 1), date(2026, 1, 31))

    assert ticker.history_kwargs["interval"] == "1mo"
    assert ticker.history_kwargs["auto_adjust"] is False
