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

## `POST /api/calculations`

Calculate historical statistics from saved daily adjusted prices.

```json
{
  "tickers": ["AAPL", "MSFT"],
  "start_date": "2026-09-01",
  "end_date": "2026-09-30"
}
```

**200:** Returns normalized tickers, requested dates, shared return intervals, daily returns, daily/annualized means and variances, covariance matrices, correlation, observation/dropped-period counts, assumptions, source metadata, and warnings. Vectors follow ticker order; both matrix axes use that order. Undefined correlations are JSON `null` with an `undefined_correlation` warning. Missing shared periods have a `dropped_intervals` warning. OpenAPI documents the complete response model.

**422:** Invalid body fields use FastAPI's standard validation response. Service errors use `{"detail": {"code": "...", "message": "..."}}`, including `invalid_calculation_input`, `invalid_price_history`, `insufficient_history`, `unsupported_period`, and `invalid_calculation_result`.

**503** `price_history_unavailable`: Stored prices cannot be read. The default reader currently always reports this error for otherwise valid requests; the real database reader is not connected yet. This endpoint does not retrieve prices from an external provider.

Configuration: `CALCULATION_CALENDAR` defaults to `XNYS`; `CALCULATION_ANNUALIZATION_FACTOR` defaults to `252` and must be positive and finite. Compose forwards both values to the API. See [the calculation spec](../docs/specs/calculations.md) for formulas and integration requirements.

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
