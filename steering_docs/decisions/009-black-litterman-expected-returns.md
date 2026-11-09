# Decision 009 — Black–Litterman expected returns

- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Christian Ayad
- **Ticket:** SCRUM-37

## Context

The strategies need the expected return of each stock. Before this decision, they used the mean return of the selected period (the historical mean). This mean has a large error. The standard error of a yearly mean is σ/√T, with σ the yearly volatility and T the number of years. For a stock with 30% volatility and 1 year of data, the error is ±30 points.

Mean-variance optimization makes this error larger. With historical means, the strategies gave corner portfolios (most of the money in one or two stocks), weights that changed much from year to year, and refused runs. The Sharpe ratio that max Sharpe promised was 3 to 8 times the Sharpe ratio of the next year (refer to "Evidence").

## Decision

`BlackLittermanEstimator` (`backend/app/optimization/black_litterman.py`) calculates the expected returns. `OptimizationService` gives them to every strategy in place of the historical means.

- **Prior:** the CAPM equilibrium excess return of each stock, π = β × ERP. β = cov(stock, market) / var(market). The market is the S&P 500 index, through the ETF SPY. The uncertainty of the prior is τΣ.
- **Views:** the historical mean minus the risk-free rate, one view for each stock (P = I). The uncertainty of the views is Ω = Σ/T.

Both uncertainties are multiples of Σ, so Σ cancels. With k = τ × T:

expected return = r_f + (π + k × (historical mean − r_f)) / (1 + k)

The history gets the weight k / (1 + k) = T / (T + 1/τ). With τ = 0.05, this is T / (T + 20): 4.8% for 1 year, 13% for 3 years and 33% for 10 years.

| Setting | Value | Use |
| --- | --- | --- |
| `equity_risk_premium` | 0.05 | The ERP in the prior |
| `market_proxy_ticker` | `"SPY"` | The market index |
| `black_litterman_tau` | 0.05 | τ, the uncertainty of the prior |

What the data of the period is used for:

- Σ and β always come from the period: the sample covariance of the daily returns that the stocks and SPY share.
- The historical means are used only as views.
- T is the number of shared daily returns divided by `annualization_factor`.
- The result shows one assumption line with the ERP, τ, the years of history and the weight of the history.

## Why each choice

- **The equilibrium prior:** He and Litterman (1999). The equilibrium returns do not depend on the noise of one period. The PyPortfolioOpt documentation calls historical means "a completely uninformative prior".
- **The market is the S&P 500 index:** the covariance of each stock with the market is Σ·w_mkt. The index already holds the market caps. Thus the app needs no market-cap data, and ETF picks work.
- **A fixed ERP:** Kroll's recommended U.S. ERP, 5.0% (reaffirmed on 2 September 2026). In the prior, premium = δ × var(market). We fix the premium, not δ. Thus the prior does not change with the volatility of a short period, and it does not become negative in down years.
- **History as views:** Ω = Σ/T is the sampling distribution of a mean of T years (Pástor, 2000; QuantEcon). More years give the history more weight.
- **No user views:** new retail investors cannot give quantified views. Their risk level goes through the strategies.
- **The sample Σ:** with no user views, the posterior Σ is only a scaled Σ. We use no shrinkage: long-only rules act as shrinkage (Jagannathan and Ma, 2003), and the minimum-history rule protects Σ (Decision 005).

## How this is different from the PyPortfolioOpt built-ins

| PyPortfolioOpt built-ins | Optify |
| --- | --- |
| The prior needs market caps | β to the S&P 500 index |
| `market_implied_risk_aversion` and `capm_return` use the market mean of the period, which is noisy and negative in down years | A published ERP |
| The default Ω = τ·diag(PΣPᵀ) does not depend on T | Ω = Σ/T |
| `efficient_risk` failed on our near-singular test matrix | Our factor form solves it (Decision 005, "Target risk") |

Optify also has its own retail checks and messages.

## Evidence

Measured by hand on 2026-11-04. Test data: the 20 S&P 500 stocks of skfolio (1990 to 2022), with the S&P 500 index as the market. r_f 2%, ERP 5%, τ 0.05, cap 45%.

Formula checks (largest difference):

- β = the least-squares slope on the market: 3e-15.
- The prior = PyPortfolioOpt `market_implied_prior_returns`, with the market as the cap-weighted asset: 4e-17.
- The blend = PyPortfolioOpt `BlackLittermanModel` with P = I, Q = history and Ω = Σ/T: 4e-17.
- Max Sharpe with the prior only (no rules) = the regression of the market on the picks: 3e-15. This is the mix of the picks that moves most like the market.

Noise:

- The noise of the history in μ is at most 0.112σ for all T (largest at 20 years).
- The median β error is 0.18 at 63 days and 0.086 at 1 year. This is ±0.9 and ±0.4 points of expected return.

Down years:

- The δ of the period in PyPortfolioOpt: −2.4 (2008) and −3.9 (2022).
- Its `capm_return` put all stocks below r_f in both years.
- Black–Litterman put no stock below r_f.

Out of sample: random picks of 5 and 10 stocks, 50 investors, 2000 to 2022, each portfolio held for 1 year. History of 3 months, 1 year and 3 years.

| Max Sharpe | Historical μ | Black–Litterman |
| --- | --- | --- |
| Realized Sharpe | 0.39 to 0.61 | 0.41 to 0.58 (−0.05 to +0.02; every 95% range includes 0) |
| Promised Sharpe | 1.09 to 3.04 | 0.32 to 0.39 |
| Stocks held, 5 / 10 picks | 3.4 to 3.5 / 4.4 to 4.5 | 4.2 to 4.5 / 6.3 to 7.1 |
| Largest weight, 5 / 10 picks | 44% / 41% | 40% to 41% / 31% to 34% |
| Weight change from year to year | 27% to 68% | 22% to 50% |
| Runs refused | Up to 5.4% | 0% |

Limits of this test:

- The data has only the stocks that survived. This helps equal weights (1/N had the highest realized Sharpe, 0.51 to 0.61).
- The index has prices only, with no dividends.
- The test has no trading costs.

Measured on 2026-11-05 with Yahoo prices, through the provider, `WeekdaySessionCalendar` and `calculate_portfolio_statistics` of the app:

- **Shared days lost when SPY is added:** 0 for U.S. stocks, for U.S. ETFs, and for a portfolio with one or more U.S.-listed picks (1, 3 and 10 years). Two Toronto stocks (RY.TO, TD.TO) lost 10 of 242, 32 of 726 and 92 of 2418 days. Two Tokyo stocks (7203.T, 6758.T) lost 18 of 228, 54 of 689 and 171 of 2353 days.
- **β to SPY with same-day returns, and with the next-day effect added (Dimson, 1979), for 3 years:** AAPL 1.04 and 1.02. RY.TO 0.54 and 0.49. 7203.T 0.06 and 0.60. 6758.T 0.01 and 0.72. EWJ (a Japan ETF on NYSE) 0.88 and 0.74.
- **A real API run** (Docker Postgres, AAPL and MSFT, 2025-11-04 to 2026-11-04): the first run got 252 SPY prices and saved them. The second run used the stored prices. A run with SPY as a pick was correct. A run that failed with `insufficient_history` saved no SPY prices.

## Drawbacks

1. The expected returns that the app shows are model estimates, not history.
2. A company's own risk earns no premium (single-factor CAPM).
3. The S&P 500 holds U.S. stocks only. Thus bond, gold and foreign ETFs get a low premium.
4. Stocks on exchanges in other time zones (for example Tokyo) react to the U.S. market on the next day. Their same-day β is too low, and their prior is near the risk-free rate (refer to "Evidence"). U.S.-listed funds and ADRs trade in New York hours and do not have this problem.
5. The ERP is fixed and does not change with market conditions.
6. A run can get the SPY prices from the market data provider (refer to "Data rule"). If the provider is not available, the run fails with `market_data_unavailable` (503), also when all picks are stored. If the run fails after it got the SPY prices, the database does not keep them, and the next run gets them again.
7. The statistics use only the days on which SPY also has a return. A portfolio of only non-U.S. listings thus loses the days on which NYSE is closed (about 4% to 8% of the days; refer to "Evidence").
8. The history still moves μ, by at most about 0.11σ.
9. All numbers that use μ change: the weights (but not for minimum variance), the expected returns, the Sharpe ratios and the limits of the target return.

## Later improvements

- A time-varying ERP: the monthly implied ERP of Damodaran.
- A β with the next-day effect (Dimson, 1979) for stocks on exchanges in other time zones (refer to drawback 4).

## Data rule

`OptimizationService` loads the market index with `MarketDataService.get_or_fetch_history` (database first). This is the only exception to the stored-prices-only rule of Decision 008. The picks still use stored prices only.

## Sources

- He, G. and Litterman, R. (1999). *The Intuition Behind Black–Litterman Model Portfolios*. Goldman Sachs.
- Pástor, Ľ. (2000). "Portfolio Selection and Asset Pricing Models". *Journal of Finance*, 55(1).
- Jagannathan, R. and Ma, T. (2003). "Risk Reduction in Large Portfolios: Why Imposing the Wrong Constraints Helps". *Journal of Finance*, 58(4).
- Dimson, E. (1979). "Risk Measurement When Shares Are Subject to Infrequent Trading". *Journal of Financial Economics*, 7(2).
- Palomar, D. P. *Portfolio Optimization*, and his slides "Shrinkage and Black–Litterman".
- QuantEcon, "Two Modifications of Mean-Variance Portfolio Theory".
- Kroll, recommended U.S. equity risk premium (5.0%, reaffirmed on 2 September 2026).
- PyPortfolioOpt documentation, "Black-Litterman Allocation".
