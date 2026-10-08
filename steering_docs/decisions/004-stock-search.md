# Decision 004 — Stock search

Search for stocks with `StockService.search_stocks`, through `MarketDataProvider.search_stocks`. The yfinance provider uses `yfinance.Search`.

## Rules

- The provider asks only for stock results (no news, lists, or private companies). `MARKET_DATA_SEARCH_LIMIT` sets the number of results to request (default 10). The type filter can remove some of them.
- The service shows only the security types in `SUPPORTED_SECURITY_TYPES`. Validation (Decision 003) uses the same setting, so a user finds only stocks that they can add.
- No match is a success with an empty list. It is not an error.
- When Yahoo sends a bad answer, yfinance gives an empty response. An answer with no match still has data. Thus the provider changes only an empty response to `MarketDataUnavailableError`.
- This behavior and the unknown-symbol rule in Decision 003 are true for yfinance 0.2.61 and 1.7.0 (the Docker image). Both need the yfinance default `hide_exceptions = True`.

## Result mapping

| Result | Response |
| --- | --- |
| One or more matches | 200, `results` has items |
| No match | 200, `results` is empty |
| Empty or missing query | 422 `invalid_search_query` |
| Provider fails | 503 `market_data_unavailable` |
