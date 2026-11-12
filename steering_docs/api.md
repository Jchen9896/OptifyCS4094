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

All portfolio routes require `Authorization: Bearer <Clerk session token>`. The API
derives the owner from the verified session. Missing or invalid sessions return
**401**. A `user_id` query parameter cannot select another owner (Decision 011).

## Chat assistant (Decision 013)

Authenticated routes under `/api/chat`:

- `POST /api/chat/sessions` — create a session
- `POST /api/chat/sessions/{id}/messages` — send a user message (`content`, optional `active_portfolio_id`); returns `reply`, Learn `citations`, and `pending_tools`
- `POST /api/chat/sessions/{id}/confirm` — `{ tool_call_id, accept }` for proposed write tools

Requires `GEMINI_API_KEY`. Missing key returns **503**. Write tools never run until confirm. Trade and brokerage vault tools are not available.

## `PATCH /api/portfolios/{portfolio_id}`

Renames one portfolio. The portfolio must belong to the signed-in account (Decision 009).

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

## `DELETE /api/portfolios/{portfolio_id}`

Deletes one portfolio and its holdings. The portfolio must belong to the signed-in account.

**204** with an empty body when the delete succeeds.

**404** `portfolio_not_found` if the portfolio does not exist or another user owns it.

## `POST /api/portfolios`

Creates a portfolio for the signed-in account (Decisions 010 and 011). The service trims the name and validates every ticker before a write. Holdings and setup are optional.

```json
{
  "name": "Core",
  "holdings": [{ "symbol": "AAPL", "quantity": "10.500000" }],
  "setup": {
    "initial_capital": 1050,
    "start_date": "2026-01-01",
    "end_date": "2026-02-01",
    "strategy": "min_variance",
    "max_weight": 1,
    "risk_free_rate": 0.04,
    "weights": { "AAPL": 100 },
    "reference_prices": { "AAPL": 100 }
  }
}
```

**201** returns `id`, `user_id`, `name`, `created_at`, `setup`, and `holdings`. Each holding has `symbol`, stored stock `name`, and decimal-string `quantity`.

Setup uses the current optimizer names, `min_variance` and `max_sharpe`. The old `minvar` and `mvo` values are accepted and returned as `min_variance`.

**404** `ticker_not_found` for an unknown ticker.

**409** `duplicate_portfolio_name` for a duplicate name within one user.

**422** `invalid_portfolio_name` for a blank name; ticker validation errors follow Decision 003. Invalid quantities, duplicate normalized symbols, and invalid setup inputs return FastAPI validation errors. Quantity must be positive and fit `NUMERIC(18,6)`. Setup weights and prices must use exactly the holding symbols.

**503** `market_data_unavailable` if ticker validation cannot reach the provider.

## `GET /api/portfolios`

**200** returns a JSON array of portfolio metadata (`id`, `user_id`, `name`, `created_at`), newest first. An account with no portfolios gets `[]`. The list contains only rows for the signed-in account. Reads do not call a market data provider.

## `GET /api/portfolios/{portfolio_id}`

**200** returns the same detail fields as create, including stored quantities and the optional setup snapshot. Old portfolios can have `setup: null`.

**404** `portfolio_not_found` if the portfolio is missing or has another owner.

## `POST /api/portfolios/{portfolio_id}/optimization-runs`

Saves one completed analysis for an owned portfolio (Decision 012). Requires a Clerk session. `POST /api/optimizations` stays open without a session and does not write this table.

**Request**

```json
{
  "params": {
    "tickers": ["AAPL", "MSFT"],
    "start_date": "2025-01-01",
    "end_date": "2025-06-01",
    "strategy": "min_variance",
    "max_weight": 0.6,
    "risk_free_rate": 0.04,
    "initial_capital": 10000,
    "current_weights": [0.5, 0.5]
  },
  "result": {
    "strategy": "min_variance",
    "weights": { "AAPL": 0.4, "MSFT": 0.6 },
    "expected_return": 0.08,
    "volatility": 0.12,
    "sharpe_ratio": 0.33,
    "current_expected_return": 0.07,
    "current_volatility": 0.14,
    "current_sharpe_ratio": 0.21,
    "period_start": "2025-01-01",
    "period_end": "2025-06-01",
    "assumptions": [],
    "initial_capital": 10000,
    "equity_curve": []
  }
}
```

**201** returns `id`, `portfolio_id`, `params`, `result`, and `created_at`.

**404** `portfolio_not_found` if the portfolio is missing or has another owner.

## `GET /api/portfolios/{portfolio_id}/optimization-runs`

**200** returns recent runs for the owned portfolio, newest first. Each row has `id`, `portfolio_id`, `strategy`, `period_start`, `period_end`, `expected_return`, `volatility`, `sharpe_ratio`, and `created_at`. Optional `limit` defaults to 20 (max 100).

**404** `portfolio_not_found` if the portfolio is missing or has another owner.

## `GET /api/portfolios/{portfolio_id}/optimization-runs/{run_id}`

**200** returns the full stored run (`params` + `result`).

**404** `portfolio_not_found` if the portfolio is missing or has another owner.

**404** `optimization_run_not_found` if the run is missing for that portfolio.

## Community forum

All routes under `/api/community` require a valid Clerk session. The API resolves the signed-in account and ignores caller-supplied author fields. Responses expose the public name and optional avatar, never an email address or Clerk subject. Missing or invalid names display as `Member`.

- `GET /api/community/categories` returns the seeded `question`, `discussion`, and `portfolio` categories.
- `POST /api/community/posts` creates a post with `title`, `body`, and `category`.
- `GET /api/community/posts` lists posts newest first. Optional `category`, `cursor`, and `limit` filters apply.
- `GET /api/community/posts/{post_id}` reads one post.
- `PATCH /api/community/posts/{post_id}` edits `title`, `body`, or `category` for the author.
- `DELETE /api/community/posts/{post_id}` deletes the post and its entire reply tree.
- `GET /api/community/posts/{post_id}/replies` lists direct children only. Optional `parent_reply_id`, `cursor`, and `limit` select a sibling page.
- `POST /api/community/posts/{post_id}/replies` adds a reply with `body` and optional `parent_reply_id`.
- `PATCH /api/community/posts/{post_id}/replies/{reply_id}` edits the reply body for its author.
- `DELETE /api/community/posts/{post_id}/replies/{reply_id}` replaces the reply body with a tombstone. Descendants remain available.

Post titles are limited to 160 characters, post bodies to 10,000, and reply bodies to 4,000. Page size defaults to 20 and cannot exceed 50. Cursors are opaque, versioned, and bound to the category or post and parent scope. A malformed cursor or a cursor from another scope returns **422** `invalid_cursor`. Posts sort newest first. Replies sort oldest first. Both use UUIDs to break timestamp ties.

An edit sets `edited_at`. A reply tombstone has a null body and author, plus `deleted_at`. A deleted reply cannot be edited. The same author can repeat the delete request and receives **204**. A missing item and an item owned by another account return the same **404**.

Deleting an account anonymizes its Community posts and replies by setting author references to null. The content remains. The forum then displays `Member` for an anonymized post and hides the tombstoned reply author. Account export contains only the signed-in user's own Community posts and replies.
