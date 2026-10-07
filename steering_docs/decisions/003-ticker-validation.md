# Decision 003 — Ticker validation

Confirm each ticker with `StockService.validate_ticker` in `backend/app/services/stock_service.py` before a user adds it.

## Rules

- The service removes spaces and changes the symbol to upper case. Then it checks the format with `TICKER_PATTERN`. A bad format does not cause a provider call.
- A provider raises `TickerNotFoundError` when it does not know a symbol. yfinance 0.2.61 does not raise an error for an unknown symbol. It returns data with no `quoteType`, so the provider uses a missing `quoteType` as the signal.
- The service accepts only the security types in `SUPPORTED_SECURITY_TYPES` (default `EQUITY,ETF`).
- This change has no API endpoint. The "add to portfolio" route calls the service.

## Error mapping

| Result | Code | HTTP |
| --- | --- | --- |
| Bad symbol format | `invalid_ticker_format` | 422 |
| Provider does not know the symbol | `ticker_not_found` | 404 |
| Security type is not supported | `unsupported_security` | 422 |
| Provider fails (network, rate limit, bad data) | `market_data_unavailable` | 503 |
