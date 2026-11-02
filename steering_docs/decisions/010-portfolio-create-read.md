# Decision 010 - Portfolio create and read

Build on Decision 009 and PR #26. Keep its tables and owner query parameter.

## Decision

- `POST /api/portfolios?user_id=<uuid>` creates a named portfolio for an existing user. The request can include holdings with positive share quantities.
- `GET /api/portfolios?user_id=<uuid>` lists that user's portfolios, newest first. An unknown user gets an empty list.
- `GET /api/portfolios/{portfolio_id}?user_id=<uuid>` reads one owned portfolio with holdings. A wrong owner gets the same 404 as a missing portfolio.
- Use the existing name errors. Return `portfolio_user_not_found` (404) when a create request names a user that does not exist.
- Validate all holding tickers through `StockService` before a database write. Save the shared stock rows, the portfolio, and the holdings in one request transaction.
- Read requests use stored rows only. They do not call a market data provider.
- Add a nullable JSON `portfolios.setup` column. A typed API schema checks its initial capital, dates, strategy, allocation weights, reference prices, and analysis settings. Old portfolios can keep `setup = null`.
- Store the current optimizer names, `min_variance` and `max_sharpe`. Read old `minvar` and `mvo` snapshots as `min_variance`, which was their original behavior.
- Keep share quantities in `portfolio_holdings`. Keep setup weights and reference prices in the snapshot so reopening a portfolio does not need a new market price or change the user's inputs.
- The setup page saves a new portfolio. It does not overwrite an existing portfolio. A duplicate name shows the existing conflict error.
- The setup page lists and loads saved portfolios after the user enters an existing user UUID. It must state that sign-in is not available yet. Do not create a shared user or trust a client UUID after authentication is added.
- A portfolio with no setup snapshot remains readable through the API. The setup page explains that its allocation inputs are not available.

## Why

The setup page edits weights, dates, and initial capital. Quantities alone cannot restore those inputs. One optional snapshot preserves them without changing the shared stock and price tables or the holding quantity contract.

## Delivery to main

PRs #27-#32 reviewed the storage, schemas and repository, service rules, HTTP routes, frontend client, and Save/Load controls as small changes. They were merged into feature branches after PR #26 had merged into `main`. Their changes did not reach `main`.

The contributor requested one replacement PR directly into `main` for the complete feature. This delivery exceeds the usual line and file limits because it carries the six reviewed changes together. Keep their separate commits and add the strategy compatibility checks needed for current `main`. Do not change `coding-style.md` or merge the replacement PR without review.

## Deferred

Authentication, user registration, holding update/delete routes, and edits to saved allocations stay in their own work. The user UUID query parameter is an interim development contract, not authentication.
