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
