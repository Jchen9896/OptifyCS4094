"""Unit tests for converting provider data into the internal format."""

from datetime import date

import pandas as pd

from app.market_data.base import PriceBar, StockInfo
from app.market_data.normalizers import normalize_price_frame, normalize_search_quote, normalize_stock_info


def make_frame(rows: dict[str, list], index: list[str], tz: str | None = None) -> pd.DataFrame:
    return pd.DataFrame(rows, index=pd.DatetimeIndex(index, tz=tz))


def test_price_frame_becomes_price_bars():
    frame = make_frame(
        {"Open": [10.0], "High": [12.0], "Low": [9.5], "Close": [11.0], "Volume": [1000]},
        ["2026-01-02"],
    )

    assert normalize_price_frame(frame) == [
        PriceBar(date=date(2026, 1, 2), open=10.0, high=12.0, low=9.5, close=11.0, volume=1000)
    ]


def test_price_frame_is_sorted_oldest_first():
    frame = make_frame(
        {"Open": [2.0, 1.0], "High": [2.0, 1.0], "Low": [2.0, 1.0], "Close": [2.0, 1.0], "Volume": [2, 1]},
        ["2026-01-05", "2026-01-02"],
    )

    assert [bar.date for bar in normalize_price_frame(frame)] == [date(2026, 1, 2), date(2026, 1, 5)]


def test_rows_with_missing_price_are_removed():
    frame = make_frame(
        {"Open": [1.0, 2.0], "High": [1.0, 2.0], "Low": [1.0, 2.0], "Close": [1.0, None], "Volume": [1, 2]},
        ["2026-01-02", "2026-01-05"],
    )

    assert [bar.date for bar in normalize_price_frame(frame)] == [date(2026, 1, 2)]


def test_missing_volume_becomes_zero():
    frame = make_frame(
        {"Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [None]},
        ["2026-01-02"],
    )

    assert normalize_price_frame(frame)[0].volume == 0


def test_time_zone_index_keeps_exchange_trading_day():
    frame = make_frame(
        {"Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [1]},
        ["2026-01-02 00:00"],
        tz="America/New_York",
    )

    assert normalize_price_frame(frame)[0].date == date(2026, 1, 2)


def test_empty_price_frame_gives_empty_list():
    frame = make_frame({"Open": [], "High": [], "Low": [], "Close": [], "Volume": []}, [])

    assert normalize_price_frame(frame) == []


def test_stock_info_uses_long_name_first():
    info = {
        "longName": "Apple Inc.",
        "shortName": "Apple",
        "currency": "USD",
        "exchange": "NMS",
        "quoteType": "EQUITY",
    }

    assert normalize_stock_info("AAPL", info) == StockInfo(
        symbol="AAPL", name="Apple Inc.", currency="USD", exchange="NMS", quote_type="EQUITY"
    )


def test_stock_info_falls_back_to_short_name_then_symbol():
    assert normalize_stock_info("AAPL", {"shortName": "Apple"}).name == "Apple"
    assert normalize_stock_info("AAPL", {}).name == "AAPL"


def test_stock_info_missing_fields_are_none():
    stock = normalize_stock_info("AAPL", {})

    assert stock.currency is None
    assert stock.exchange is None
    assert stock.quote_type is None


def test_search_quote_falls_back_to_short_name_then_symbol():
    assert normalize_search_quote({"symbol": "SPY", "shortname": "SPDR"}).name == "SPDR"
    assert normalize_search_quote({"symbol": "SPY"}).name == "SPY"
