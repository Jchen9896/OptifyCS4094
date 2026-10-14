# Decision 005 — Calculation inputs

## Decision

Calculate returns from the existing `PriceBar` type and a supplied list of expected trading sessions. Keep provider calls and database queries outside the calculation functions.

Use adjusted daily close prices and simple decimal returns. Skip an interval when either endpoint price is missing. Do not fill a missing price or calculate across a missing trading session.

## Why

The provider can remove incomplete price rows. Consecutive returned rows can therefore cover more than one trading session. A separate session list prevents us from calling those changes daily returns.

## Integration

- The stored-history reader must provide saved source, retrieval time, adjustment basis, interval, exchange, and calendar metadata. Current settings cannot prove how old records were collected.
- The service must check that metadata before calling the calculation functions. The functions use `PriceBar.close`; they do not adjust prices themselves.
- The calculation service will supply annualized means and covariance to the existing optimizer input, in ticker order. Single-stock analysis is allowed; optimizer input requires at least two stocks.
- Use the existing `AppError` format for invalid calculation inputs.

The full integration and test requirements are in [the calculation spec](../../docs/specs/calculations.md).
