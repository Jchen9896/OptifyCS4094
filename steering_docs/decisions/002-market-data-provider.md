# Decision 002 — Market data provider

Get all stock data through the `MarketDataProvider` interface in `backend/app/market_data/base.py`. Use **yfinance** as the first provider.

## Rules

- Application code uses only `StockInfo` and `PriceBar`. It does not use raw provider data (for example, a yfinance `DataFrame`).
- A provider converts its data with the functions in `normalizers.py`.
- A provider changes all of its own errors to `MarketDataUnavailableError` (`market_data_unavailable`, HTTP 503).
- A provider gets its settings (`MARKET_DATA_INTERVAL`, `MARKET_DATA_AUTO_ADJUST`) from `Settings` through its constructor.
- Tests give a fake ticker factory to the provider. Unit tests do not use the network.

## Error mapping

| Provider result | Application result |
| --- | --- |
| Any exception from yfinance (network, rate limit, bad data) | `MarketDataUnavailableError` (503) |
| No price rows | Empty list |
| No stock name | Symbol is used as the name |

Ticker validation is not part of this decision. Refer to Decision 003. An unknown symbol gives `TickerNotFoundError` (404), not `MarketDataUnavailableError`.

## Add a new provider

1. Make a subclass of `MarketDataProvider` in `backend/app/market_data/`.
2. Convert the data to `StockInfo` and `PriceBar`.
3. Change provider errors to `MarketDataUnavailableError`.
4. Give the new provider to the services in place of `YFinanceProvider`. Portfolio logic does not change.
