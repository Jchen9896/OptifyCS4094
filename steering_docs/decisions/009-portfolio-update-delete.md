# Decision 009 — Portfolio update and delete

Add rename and delete for a saved portfolio. Do not add create or read routes in this change.

## Decision

- Store rows in `users`, `portfolios`, and `portfolio_holdings` as in database design v3.
- `portfolios.user_id` references `users.id`. A portfolio name is unique for one user.
- `portfolio_holdings` references `portfolios.id` with `ON DELETE CASCADE`. A portfolio delete removes its holdings.
- Expose only these routes:
  - `PATCH /api/portfolios/{portfolio_id}?user_id=<uuid>` renames the portfolio.
  - `DELETE /api/portfolios/{portfolio_id}?user_id=<uuid>` deletes the portfolio.
- The service loads the row only when `user_id` owns `portfolio_id`. A missing row and a wrong owner both return `portfolio_not_found`.
- Reject a blank name with `invalid_portfolio_name`. Reject a duplicate name for the same user with `duplicate_portfolio_name`.
- Pass `user_id` as a query parameter until login exists. When login exists, take the user id from the session. Do not trust a client-supplied user id after that.
- Do not add `optimization_runs` here. When that table is added, delete its rows with the portfolio (database design v3).

This change edits more than three files and more than 200 lines. The repository already separates the model, the migration, the repository, the service, the schema, and the route. The migration repeats the table definitions, and `users` exists only because `portfolios.user_id` references it. Each file stays in that layer. The behavior is update and delete only.

## Why

- Database design v3 says a user owns portfolios and holdings belong to one portfolio.
- Update and delete need the foreign keys now, so a later create route can use the same tables.
- The same not-found response for a wrong owner does not show that another user's portfolio exists.
- Login is still deferred (Decision 007). The ownership check is in the service so a later auth dependency can supply `user_id`.

## Deferred

- Create a portfolio and list or read portfolios.
- Add, update, and remove holdings through HTTP.
- Map setup-page weights to `portfolio_holdings.quantity`.
- Replace the `user_id` query parameter with the authenticated user.
