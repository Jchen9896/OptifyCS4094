# Optify calculation spec and implementation plan

Status: Steps 1–3 are implemented for review: daily returns, shared return periods, average/annualized returns, variance, covariance, and correlation, with tests. Storage integration, optimizer handoff, and the API remain pending.

## Summary

Implement Newton's five assigned tickets as a reusable calculation module and a stored-history API:

| Ticket | Deliverable |
|---|---|
| [SCRUM-16](https://vt-team-n8fy630g.atlassian.net/browse/SCRUM-16) | Daily returns and interval alignment |
| [SCRUM-17](https://vt-team-n8fy630g.atlassian.net/browse/SCRUM-17) | Average and annualized returns |
| [SCRUM-18](https://vt-team-n8fy630g.atlassian.net/browse/SCRUM-18) | Variance and covariance |
| [SCRUM-19](https://vt-team-n8fy630g.atlassian.net/browse/SCRUM-19) | Correlation matrix |
| [SCRUM-20](https://vt-team-n8fy630g.atlassian.net/browse/SCRUM-20) | Hand-calculated fixtures, edge cases, and CI |

The audience is the frontend team and Christian's optimizer. UI work, optimization algorithms, and market-data ingestion remain outside this implementation.

## Review steps

Work in small steps and pause after each step for Newton's review:

1. Daily returns for one stock, with known-answer and missing-day tests.
2. Match return intervals across stocks, then calculate averages and annualized returns.
3. Calculate variance, covariance, and correlation.
4. Connect saved price histories and map results into the optimizer input.
5. Add the calculation API, storage integration tests, and CI.

## Calculation rules

- Use split- and dividend-adjusted daily closing prices. Require the data source to identify that basis; do not silently substitute raw close.
- Calculate simple returns: `r = current_price / previous_price - 1`. Return decimals, so `0.05` means 5%.
- Use consecutive exchange sessions within the inclusive requested date range. The first price is a baseline; do not fetch an earlier price outside the range.
- Use an injected session-calendar interface, backed by `exchange_calendars` with `XNYS` for the U.S. equity MVP. Weekends and exchange holidays are normal closures. [Calendar library](https://github.com/gerrymanoim/exchange_calendars)
- If either endpoint price is missing for any selected stock, drop that interval for every stock. Never fill missing prices or bridge a missing trading session.
- Compute every returned statistic from the same aligned return matrix. Rows represent intervals; columns follow the requested ticker order.
- Sort observations by date. Reject duplicate security/date records, non-session observations, nonpositive prices, non-finite values, and incompatible price bases.
- Require at least two aligned returns for the combined result. The daily-return helper may return one interval; the combined API reports insufficient history.

| Statistic | Formula |
|---|---|
| Daily arithmetic mean | `sum(returns) / n` |
| Annualized arithmetic mean | `daily_mean × A` |
| Sample covariance | `sum((ri − mean_i)(rj − mean_j)) / (n − 1)` |
| Daily variance | Diagonal of daily covariance |
| Annualized covariance/variance | Daily value × `A` |
| Correlation | `cov(i,j) / sqrt(var_i × var_j)` |

Use configurable `A = 252`. This is a trading-year convention, not the exact session count for every year. Annualized arithmetic mean does not include compounding. Sample covariance uses `ddof=1`. [NumPy covariance documentation](https://numpy.org/doc/stable/reference/generated/numpy.cov.html)

For zero-variance securities, return `null` for all affected correlation cells, including their diagonal, and include a warning. Other diagonal cells equal 1. Correlation is symmetric and bounded by −1 and 1; clamp rounding drift only. [NumPy correlation documentation](https://numpy.org/doc/stable/reference/generated/numpy.corrcoef.html)

## Interfaces and data flow

### Core module

Implement pure functions in `backend/app/services/calculation_service.py`. Use the existing NumPy dependency for float64 matrix calculations. Keep database access, HTTP handling, and provider calls outside the calculation functions.

Step 1 adds `calculate_daily_returns(prices, sessions) -> list[DailyReturn]`. It accepts the existing `PriceBar` objects and an ordered, unique list of expected trading dates. Each result includes `start_date`, `end_date`, and a decimal `value`. Input prices can arrive in any order. Invalid dates, duplicate prices, nonpositive/non-finite closes, and non-finite returns raise `AppError` with code `invalid_price_history` and HTTP status 422. Empty or one-price histories return no intervals. The later combined calculation service still requires at least two aligned returns.

Step 2 adds `calculate_return_summary(histories, tickers, sessions, annualization_factor) -> ReturnSummary`. It matches both dates of each return period across all selected stocks, preserves the supplied ticker order, and requires at least two shared periods. It returns the shared periods, daily return rows, daily/annualized means, annualization factor, observation count, and dropped-period count. The count of dropped periods is the number of consecutive pairs in the supplied session list minus the number used. The annualization factor is a required input; the later service will supply the configured default of 252. Empty/duplicate tickers and invalid factors give `invalid_calculation_input`; missing or insufficient shared prices give `insufficient_history`; non-finite averages give `invalid_calculation_result`. These errors use HTTP 422.

Step 3 adds `calculate_risk_statistics(summary) -> RiskStatistics`. It uses Step 2's shared daily returns to calculate sample covariance (`ddof=1`) and its diagonal variances. Annualized covariance and variance use the same supplied annualization factor. Correlation is derived from daily covariance, is symmetric, and is not annualized. Rows and columns preserve `summary.tickers`, including a one-stock 1×1 matrix. Zero-variance stocks have `None` in all affected correlation cells, including the diagonal, plus a coded `undefined_correlation` warning naming the stock. The future API will serialize these missing cells as JSON `null`. Non-finite statistics raise `invalid_calculation_result` with HTTP 422.

Expose an aggregate calculation function that accepts ticker order, dated adjusted-price observations, expected sessions, and the annualization factor. Return a typed result containing aligned returns, means, covariance, variance, correlation, and data-quality metadata. Christian's optimizer can consume annualized means and covariance directly without an HTTP call.

### History integration

Define an injectable `PriceHistoryReader` interface:

```text
read_adjusted_history(tickers, start_date, end_date) -> PriceHistoryBatch
```

The batch groups existing `PriceBar` objects by normalized ticker. For each history, require saved metadata: source, retrieval timestamp, adjustment basis, interval, exchange, and calendar. Fetch one batch per request.

Joey's ingestion/storage code must save that metadata and return it with the prices. Current application settings do not prove how previously stored prices were obtained. The calculation service must require daily (`1d`) prices adjusted for splits and dividends, plus a calendar compatible with the MVP's XNYS schedule. Reject missing or incompatible metadata. A stock passing the existing ticker validation does not prove its market uses that calendar.

Use `PriceBar.close` only after those checks. Do not adjust the prices again. The provider's normalizer removes incomplete OHLC rows, so build return intervals from expected sessions, not adjacent returned bars.

Joey's [SCRUM-11–13](https://vt-team-n8fy630g.atlassian.net/browse/SCRUM-13) provide retrieval, validation, and storage. Implement the thin reader adapter after that code is available. Until then, use an in-memory reader in tests; do not ship sample data as the production source. Production integration is a release dependency.

The stored-history reader reads through the price repository. It must not call the market-data provider or `StockService.validate_ticker`, which contacts the provider. Data retrieval remains a separate operation.

### Optimizer integration

Map calculation results into the existing `OptimizerInput`:

| Calculation result | Optimizer field |
|---|---|
| Ordered tickers | `tickers` |
| Annualized mean returns | `expected_returns` |
| Annualized covariance | `covariance` |
| Requested start/end dates | `period_start` / `period_end` |

Use annual decimal units for returns and covariance. A supplied risk-free rate must also be an annual decimal. The optimization service supplies `strategy`, `max_weight`, and `risk_free_rate`; the calculation module does not choose them.

The optimization service must assemble and validate `OptimizerInput` with `validate_optimizer_input`, then pass the resulting NumPy arrays to `OptimizationStrategy.compute_weights`. Preserve the same ticker order in each vector and both matrix axes. Single-stock calculations remain supported, but optimizer handoff requires at least two stocks. Carry the calculation assumptions into `OptimizationResult.assumptions`.

### HTTP endpoint

Add and register:

```http
POST /api/calculations
```

```json
{
  "tickers": ["AAA", "BBB"],
  "start_date": "2026-09-01",
  "end_date": "2026-09-30"
}
```

Normalize ticker whitespace and case, preserve order, and reject empty or duplicate tickers. Require `start_date < end_date`.

The response contains:

- `tickers`, requested dates, `intervals` with start/end dates, and `daily_returns` as an interval-by-ticker matrix.
- `daily_mean_returns`, `annualized_mean_returns`, `daily_variances`, and `annualized_variances`, each ordered by ticker.
- `daily_covariance`, `annualized_covariance`, and `correlation`, with the same ticker order on both axes.
- `observation_count`, `dropped_interval_count`, and coded warnings for missing intervals or undefined correlation.
- Assumptions: price basis, simple-return formula, arithmetic annualization, factor, sample denominator, and calendar.
- Source metadata from the history reader.

Use HTTP 422 for invalid requests, unusable stored data, unsupported calendar ranges, and insufficient aligned history. Use the existing `AppError` envelope for calculation errors. Use HTTP 503 for unavailable storage; distinguish it from an empty history. Do not trigger provider downloads through this endpoint.

## Implementation sequence

1. **Contract and documentation:** Record this spec in `docs/specs/calculations.md`; add an ADR for price basis, alignment, and annualization. Define result types and injectable history/calendar interfaces.
2. **SCRUM-16:** Implement validation, session-aware interval construction, simple returns, and alignment, with tests.
3. **SCRUM-17:** Add daily means, configurable annualization, and assumption metadata.
4. **SCRUM-18:** Add sample covariance and variance, including the single-security matrix case.
5. **SCRUM-19:** Derive correlation from covariance; handle zero variance and warnings.
6. **API integration:** Add request/response schemas and the thin route, test with an injected reader, then connect Joey's stored-history implementation.
7. **SCRUM-20:** Complete independent fixtures and CI. Run backend pytest on pull requests and pushes to `main`, using Python 3.12. Add PostgreSQL-backed integration checks when the storage adapter is connected.

Write tests with each calculation increment. Follow repository limits of approximately 200 source lines and 200 test lines per reviewable change, normally at most three files. Explain any exception and follow the required commit format. Preserve the existing local `compose.yaml` change.

## Test plan and completion criteria

- Hand-calculated fixture: `AAA = [100,110,99]`, `BBB = [100,90,99]` over three consecutive sessions. Expected means: zero; variances: `0.02`; covariance: `−0.02`; correlation: `−1`; annualized variances: `5.04`.
- Cover positive correlation, one security, constant prices, constant nonzero returns, and zero-variance correlation.
- Verify weekend/holiday intervals remain valid. A missing trading-day price must remove both affected intervals without producing a multi-session return.
- Cover empty histories, one return, disjoint histories, unsorted data, duplicate dates, invalid prices, adjustment-basis mismatch, and unsupported date ranges.
- Verify covariance symmetry, diagonal/variance agreement, ticker ordering, matrix dimensions, annualization scaling, and finite JSON output. Compare numeric fixtures within `1e-12`.
- Exercise API success and error cases using dependency overrides, with no network requests.
- Verify saved price metadata survives storage and loading. Reject raw, non-daily, undocumented, or incompatible-market history before calculations.
- Pass a history with a row removed by normalization into calculations. Verify both affected intervals are skipped.
- Map results into the actual `OptimizerInput` and check ticker order, dates, and annual units. Verify a single-stock calculation is not passed to the optimizer.
- Complete a PostgreSQL-backed stored-history request after Joey's integration lands. Fixture-only API tests do not satisfy this final integration criterion.

The provider error-handling issue and optimizer symmetry-tolerance issue found during review are separate follow-up fixes. They are not part of Newton's calculation tickets.

Completion means all five ticket requirements have passing CI checks, documented formulas, and a verified stored-history API. No UI changes or database migrations are required for the calculation module; storage migrations remain part of Joey's work.
