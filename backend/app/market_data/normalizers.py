"""Convert raw provider data into the internal stock and price format."""

from typing import Any

import pandas as pd

from app.market_data.base import PriceBar, StockInfo

# Column names of a price table (the format that yfinance and pandas use).
OPEN_COLUMN = "Open"
HIGH_COLUMN = "High"
LOW_COLUMN = "Low"
CLOSE_COLUMN = "Close"
VOLUME_COLUMN = "Volume"
PRICE_COLUMNS = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]

# Keys in a provider's stock data, in order of preference.
NAME_KEYS = ["longName", "shortName"]
CURRENCY_KEY = "currency"
EXCHANGE_KEY = "exchange"


def normalize_price_frame(frame: pd.DataFrame) -> list[PriceBar]:
    """Convert a price table with a date index into price bars, oldest first.

    Rows with a missing price are removed. A missing volume becomes 0.
    The date of each row is the trading day in the exchange time zone.
    """
    clean = frame.dropna(subset=PRICE_COLUMNS).sort_index()
    return [
        PriceBar(
            date=timestamp.date(),
            open=float(row[OPEN_COLUMN]),
            high=float(row[HIGH_COLUMN]),
            low=float(row[LOW_COLUMN]),
            close=float(row[CLOSE_COLUMN]),
            volume=0 if pd.isna(row[VOLUME_COLUMN]) else int(row[VOLUME_COLUMN]),
        )
        for timestamp, row in clean.iterrows()
    ]


def normalize_stock_info(symbol: str, info: dict[str, Any]) -> StockInfo:
    """Convert a provider's stock data into `StockInfo`.

    If the data has no name, the symbol is used as the name.
    """
    name = next((info[key] for key in NAME_KEYS if info.get(key)), symbol)
    return StockInfo(
        symbol=symbol,
        name=name,
        currency=info.get(CURRENCY_KEY),
        exchange=info.get(EXCHANGE_KEY),
    )
