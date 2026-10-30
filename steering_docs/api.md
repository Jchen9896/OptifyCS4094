# API

## `GET /api/health`

Confirms the API process is running and PostgreSQL accepts a connection.

**200**

```json
{
  "status": "ok",
  "api": "reachable",
  "database": "reachable",
  "checked_at": "2026-10-05T14:00:00+00:00"
}
```

**503** if the API is up but the database is not reachable.

## `GET /api/stocks?q=<text>`

Searches for stocks by ticker or company name. Only supported security types are returned (Decision 004).

**200**

```json
{
  "query": "apple",
  "results": [
    { "symbol": "AAPL", "name": "Apple Inc.", "exchange": "NMS", "quote_type": "EQUITY" }
  ]
}
```

An empty `results` list means that no stock matches.

**422** `invalid_search_query` if `q` is empty or missing.

**503** `market_data_unavailable` if the market data provider fails.

## `POST /api/market-data/history`

Returns daily prices for one symbol and date range (Decision 006). Prefers stored `price_bars`. Calls the market data provider only when stored rows do not cover the range.

**Request**

```json
{
  "symbol": "AAPL",
  "start_date": "2026-01-02",
  "end_date": "2026-01-31"
}
```

**200**

```json
{
  "symbol": "AAPL",
  "start_date": "2026-01-02",
  "end_date": "2026-01-31",
  "bar_count": 20,
  "first_date": "2026-01-02",
  "last_date": "2026-01-30",
  "source": "yfinance",
  "fetched_at": "2026-10-14T12:00:00+00:00",
  "served_from_database": false
}
```

`served_from_database` is `true` when the response came from stored rows without a provider call.

**422** `invalid_date_range` if the dates are missing, equal, reversed, or longer than `MARKET_DATA_MAX_SPAN_DAYS`.

**422** `unreliable_price_history` if provider rows have duplicates or invalid OHLCV.

**422** `insufficient_history` if the provider returns no price rows.

**404** `ticker_not_found` if the provider does not know the symbol.

**422** `invalid_ticker_format` / `unsupported_security` from ticker validation (Decision 003).

**503** `market_data_unavailable` if the market data provider fails.

## `PATCH /api/portfolios/{portfolio_id}?user_id=<uuid>`

Renames one portfolio. The portfolio must belong to `user_id` (Decision 009).

**Request**

```json
{
  "name": "Growth"
}
```

The service removes spaces at the start and end of `name`. A name that is empty after that is rejected.

**200**

```json
{
  "id": "11111111-1111-1111-1111-111111111111",
  "user_id": "22222222-2222-2222-2222-222222222222",
  "name": "Growth",
  "created_at": "2026-10-28T12:00:00Z"
}
```

**404** `portfolio_not_found` if the portfolio does not exist or another user owns it.

**422** `invalid_portfolio_name` if the name is blank.

**409** `duplicate_portfolio_name` if this user already has a portfolio with that name.

## `DELETE /api/portfolios/{portfolio_id}?user_id=<uuid>`

Deletes one portfolio and its holdings. The portfolio must belong to `user_id`.

**204** with an empty body when the delete succeeds.

**404** `portfolio_not_found` if the portfolio does not exist or another user owns it.

## `POST /api/portfolios?user_id=<uuid>`

Creates a portfolio for an existing user (Decision 010). The service trims the name and validates every ticker before a write. Holdings and setup are optional.

```json
{
  "name": "Core",
  "holdings": [{ "symbol": "AAPL", "quantity": "10.500000" }],
  "setup": {
    "initial_capital": 1050,
    "start_date": "2026-01-01",
    "end_date": "2026-02-01",
    "strategy": "minvar",
    "max_weight": 1,
    "risk_free_rate": 0.04,
    "weights": { "AAPL": 100 },
    "reference_prices": { "AAPL": 100 }
  }
}
```

**201** returns `id`, `user_id`, `name`, `created_at`, `setup`, and `holdings`. Each holding has `symbol`, stored stock `name`, and decimal-string `quantity`.

**404** `portfolio_user_not_found` for an unknown user or `ticker_not_found` for an unknown ticker.

**409** `duplicate_portfolio_name` for a duplicate name within one user.

**422** `invalid_portfolio_name` for a blank name; ticker validation errors follow Decision 003. Invalid quantities, duplicate normalized symbols, invalid setup inputs, and missing or malformed UUIDs return FastAPI validation errors. Quantity must be positive and fit `NUMERIC(18,6)`. Setup weights and prices must use exactly the holding symbols.

**503** `market_data_unavailable` if ticker validation cannot reach the provider.

## `GET /api/portfolios?user_id=<uuid>`

**200** returns a JSON array of portfolio metadata (`id`, `user_id`, `name`, `created_at`), newest first. An unknown user or a user with no portfolios gets `[]`. The list contains only rows for the supplied user. Reads do not call a market data provider.

## `GET /api/portfolios/{portfolio_id}?user_id=<uuid>`

**200** returns the same detail fields as create, including stored quantities and the optional setup snapshot. Old portfolios can have `setup: null`.

**404** `portfolio_not_found` if the portfolio is missing or has another owner.

All portfolio routes use the temporary user UUID query parameter from Decision 009. This parameter is not authentication. Use an authenticated user dependency when sign-in is added.
