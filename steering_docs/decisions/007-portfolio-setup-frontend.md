# Decision 007 — Portfolio setup frontend

Build the Optify app shell and Portfolio setup page against the WireFrame screens, using the existing stock search and historical price APIs.

## Decision

- Use `react-router-dom` with routes `/`, `/setup`, and `/compare` inside a shared `AppShell`.
- Keep the existing dark theme tokens. Do not rebuild the light Figma grayscale in this stack.
- Keep holdings in browser state with **weight percents** (wireframe model). Do not call a portfolio persistence API yet.
- Call `GET /api/stocks` for search and `POST /api/market-data/history` per selected symbol for the historical period (Decision 006, DB-first).
- Show AppError codes from history loads (`invalid_date_range`, `insufficient_history`, `unreliable_price_history`, and others) in the coverage table.
- Leave Login, Compare behavior, Dashboard charts, and “Review & run analysis” disabled until auth, comparison, and optimization HTTP work land.

## Why

- The wireframe needs a shell and setup path before optimization results are useful.
- Local weights unlock M06–M10 UI without waiting for portfolio CRUD.
- Reuse the backend history endpoint so users do not invent a second price path.

## Deferred

- Persist portfolios and map weights to `portfolio_holdings.quantity`.
- Multi-symbol history batch endpoint.
- Returning full OHLCV series to the frontend for charts.
- Auth, Learn, Preferences, Import blueprint, and light-theme pixel match.
