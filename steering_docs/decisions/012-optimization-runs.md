# Decision 012 - Optimization runs and Compare

Persist each successful analysis for an owned portfolio so Compare can place two runs side by side.

## Decision

- Add `optimization_runs` from database design v3: `id`, `portfolio_id` (CASCADE), `params` JSON, `result` JSON, `created_at`. Index `(portfolio_id, created_at DESC)`.
- `params` stores the optimizer request used for the run (tickers, dates, strategy, constraints, current weights, initial capital). `result` stores the full `OptimizationResult` payload.
- Keep `POST /api/optimizations` open without a session (Decision 011). Persistence is a separate authenticated write.
- Authenticated routes:
  - `POST /api/portfolios/{portfolio_id}/optimization-runs` saves `params` + `result` for an owned portfolio.
  - `GET /api/portfolios/{portfolio_id}/optimization-runs` lists recent runs, newest first.
  - `GET /api/portfolios/{portfolio_id}/optimization-runs/{run_id}` reads one owned run.
- Wrong owner and missing run both return `404` (`portfolio_not_found` or `optimization_run_not_found`).
- After setup analysis succeeds and a portfolio id exists, the client saves the run, then keeps the sessionStorage last-run for the dashboard.
- Compare selects two owned runs (same or different portfolios). It shows metrics, weights, risk-return markers, and equity curves from stored results. A shared period is preferred; mismatched periods show a clear warning and still render side by side without inventing a new optimization.

## Why

Session-only results cannot power a durable Compare page. Storing runs on the portfolio matches the ERD, deletes with the portfolio, and keeps guest optimize available for local and API use.

## Deferred

Server-side re-optimization when periods differ, run delete/rename UI, and replacing dashboard sessionStorage with the latest persisted run stay in later work.
