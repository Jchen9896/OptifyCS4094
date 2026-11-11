# Decision 008 — Demo optimization pipeline

## Decision

For the MVP demo path, assemble stored prices, calculations, and minimum-variance optimization in one service and expose `POST /api/optimizations`.

## Details

- Reuse `PriceRepository`, `MinimumVarianceStrategy`, `validate_optimizer_input`, and `OptimizationResult`.
- Calculations stay pure in `calculation_service.py`. The service reads only stored bars through `StoredPriceHistoryReader` (no provider fetch on optimize).
- Exception: the optimizer also loads the market index (SPY) with `MarketDataService.get_or_fetch_history`, for the Black–Litterman prior (Decision 009). The picks still use stored prices only.
- Use `WeekdaySessionCalendar` as the session list for MVP. Missing weekday prices drop return intervals. A full XNYS `exchange_calendars` adapter can replace it later without changing calculation functions.
- Annualization factor, optimizer tolerance, and default risk-free rate come from Settings.
- Frontend keeps the last run in `sessionStorage` so the dashboard can show live results without portfolio persistence.
- The setup page does not use a separate Load prices or Save portfolio control. Run analysis calls `POST /api/market-data/history` for each selected symbol, runs optimization, then creates the portfolio when the user is signed in and the name is new. Guests still get dashboard results in `sessionStorage` only.

## Why

The demo needs one working path: search → set period → run → review weights. Portfolio save/load and correlation UI remain out of scope for this pipeline.
