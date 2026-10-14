# Decision 006 — Historical price storage

Store daily prices in PostgreSQL so the application can reuse them for analysis (M06–M08). Accept an explicit start date and end date on each retrieval request (M09–M10).

## Decision

- Fetch prices only through `MarketDataProvider.get_price_history` (Decision 002).
- Confirm the ticker with `StockService.validate_ticker` before fetch and before insert (Decision 003).
- Persist shared market data in `stocks` and `price_bars` as in database design v3 (shared dataset; all users read the same rows).
- Upsert `price_bars` on primary key `(symbol, date)`. A second retrieval for the same day updates the row. It does not create a duplicate.
- Write order: upsert `stocks`, then upsert `price_bars` (foreign key on `symbol`).
- Prefer the database for user-facing history. Read `list_range` first. Call the provider only when stored rows do not cover the requested range (or when no rows exist). Do not call yfinance on every request when the data is already stored.
- One HTTP request handles one symbol. The client may call again for each selected stock.
- Expose `POST /api/market-data/history` with `symbol`, `start_date`, and `end_date`. Do not add a public GET in this work. A repository `list_range` supports tests, DB-first reads, and later calculation reads.

## Provenance

Decision 005 requires saved metadata with stored history. Current Settings alone cannot prove how old rows were collected.

Save on each `price_bars` row:

| Column | Source |
| --- | --- |
| `fetched_at` | Time of this retrieval |
| `source` | Settings (`market_data_source`) |
| `interval` | Settings (`market_data_interval`) |
| `adjustment_basis` | Derived from Settings (`market_data_auto_adjust`) |
| `calendar` | Settings (`market_data_calendar`), MVP value `XNYS` |

Keep `exchange` on `stocks` only. A reader joins `stocks` when it needs exchange.

Do not hard-code source, calendar, interval, or maximum date span in service code. Read them from Settings.

## Quality checks (M07, M10)

Before persist:

- Reject a missing, equal, or reversed date range (`invalid_date_range`).
- Reject a range longer than Settings `market_data_max_span_days` (`invalid_date_range`).
- Reject an empty provider result (`insufficient_history`).
- Reject duplicate dates, nonpositive or non-finite OHLC, or `high < low` (`unreliable_price_history`).

Incomplete OHLC rows are already removed in `normalize_price_frame`.

## Deferred

Holiday-aware missing-session detection needs an exchange calendar. That work belongs with the calculation session list (Decision 005). This decision does not add `exchange_calendars`.

A full staleness policy (refresh when `fetched_at` is too old) is deferred. Until then, treat existing rows for a date as reusable. Multi-symbol batch APIs, users, portfolios, and the calculation HTTP API are out of scope here.

## Why

- Database design v3 keeps market data shared. Serving stored bars avoids repeat provider calls for every user.
- Reuse the existing provider and ticker validation for fills and first-time loads. Do not add a second data path.
- Save provenance on the price row so calculation reads can reject incompatible history later.
- Keep each change small and reviewable. One symbol per request keeps errors simple.
