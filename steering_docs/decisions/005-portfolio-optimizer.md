# Decision 005 — Portfolio optimizer

Calculate portfolio weights with a subclass of `OptimizationStrategy` in `backend/app/optimization/base.py`. Use **CVXPY** to solve the optimization problem. The strategies are in `mean_variance.py`:

| Strategy | `name` | Goal |
| --- | --- | --- |
| `MinimumVarianceStrategy` | `min_variance` | The lowest risk (variance) |
| `MaxSharpeStrategy` | `max_sharpe` | The highest Sharpe ratio: (expected return - risk-free rate) / volatility |
| `TargetReturnStrategy` | `target_return` | The lowest risk with an expected return of at least the target |
| `TargetRiskStrategy` | `target_risk` | The highest expected return with a volatility of at most the target |

## Rules

- `validate_optimizer_input` checks the inputs before a strategy gets them. A strategy does not check them again. A strategy checks only the conditions that are specific to it, for example `check_can_beat_risk_free_rate` in max Sharpe, or a missing target.
- Every strategy gets the same four core inputs: `expected_returns`, `covariance`, `max_weight` and `risk_free_rate`. A strategy ignores the inputs that it does not need. The core inputs have no default values, so a missing input causes an error immediately. The service changes optional user inputs to real values (for example, the risk-free rate from `Settings`) before it calls a strategy.
- Inputs that only some strategies use (`target_return`, `target_volatility`) are keyword-only and have the default `None`, which means "not given". A default is permitted only when it makes the strategies that need the input fail. A default must never change a result. A strategy that needs one of these inputs and gets `None` fails with `invalid_optimization_input`.
- A strategy can add lines to the assumptions of a result through `assumptions(target_return=..., target_volatility=...)`. The default is no lines.
- `expected_returns`, `covariance` and `risk_free_rate` are yearly (annualized) values. To change daily values to yearly values, multiply them by 252.
- All strategies follow the allocation rules: the weights add up to 1, no weight is negative (long only), and no weight is above `max_weight`.
- A strategy calls `check_rules_feasible` before it solves.
- `weight_constraints` gives the solver the rules that do not depend on the size of the weights: no weight is negative, and no weight is more than `max_weight` of the total. Each strategy adds one rule that sets the size. Minimum variance uses "the weights add up to 1". Max Sharpe uses "the excess return is 1".
- A strategy gives the covariance matrix to CVXPY through `cp.psd_wrap`. Validation is the only check of the matrix. Without `psd_wrap`, CVXPY does its own stricter check (smallest eigenvalue not below about -1e-10) and can reject a matrix that validation accepted. `psd_wrap` works only in the objective. For a constraint, refer to "Target risk".
- All strategies use one solver, from the setting `optimization_solver`: **CLARABEL**. Each strategy gets the solver through its constructor and gives it to `_solve`. We do not use the CVXPY default for quadratic problems (OSQP), for these reasons:
  - OSQP solves only quadratic problems. CLARABEL also solves cone problems. A limit on volatility makes a cone problem.
  - In a target-return problem near the highest expected return that the rules permit, OSQP failed in 17 of 100 tests. CLARABEL failed in 0 of 500 tests.
  - For minimum variance and max Sharpe, CLARABEL was as fast as OSQP (about 4 to 8 ms for each solve). It had no failures in 600 tests with 2 to 50 stocks.
- `_solve` accepts only the status `optimal`. `optimal_inaccurate` and all other statuses fail.
- `_clean_and_check` calls `clean_weights` and then `find_rule_violations`. If a weight breaks a rule, the run fails.

## Maximum Sharpe ratio

The Sharpe ratio is a ratio, so CVXPY cannot maximize it directly. `MaxSharpeStrategy` uses the Schaible transform (Palomar, *Portfolio Optimization*, section 7.2):

1. The Sharpe ratio does not change when all weights are multiplied by the same positive number.
2. Thus, the strategy solves for scaled weights whose excess return is exactly 1. Then the Sharpe ratio is 1 / (volatility of the scaled weights), and the highest Sharpe ratio has the lowest risk.
3. The solver minimizes the risk of the scaled weights with the rules "excess return is 1" and `weight_constraints`.
4. The strategy divides the scaled weights by their total to get the real weights.

This works only if an allocation under the rules has an expected return above the risk-free rate. `check_can_beat_risk_free_rate` checks this before the solver. It uses `highest_expected_return`, which puts as much money as `max_weight` permits in the stocks with the highest expected returns first. If the result is not above the risk-free rate, the run fails.

Known limit: max Sharpe is very sensitive to the expected returns (Palomar, section 7.5). Small errors in the expected returns can move most of the money into one or two stocks. A `max_weight` cap decreases this problem.

## Target return

`TargetReturnStrategy` finds the allocation with the lowest risk whose expected return is at least the target. It solves problem 7.3 in Palomar, *Portfolio Optimization*, section 7.1.2:

minimize wᵀΣw, with μᵀw ≥ target return, "the weights add up to 1" and `weight_constraints`.

- The rule is "at least the target", not "equal to the target". With "equal", a target below the minimum-variance return gives an allocation with more risk and less return than minimum variance. With "at least", such a target gives the minimum-variance allocation.
- Before the solver, `check_target_return_reachable` compares the target with `highest_expected_return`. If the target is more than the tolerance above the highest return, the run fails with `unreachable_target`. The message suggests a target: the highest return, rounded down to 0.1%.
- If the target is above the highest return by less than the tolerance, the solver gets the highest return. No allocation reaches more, and a higher value can make the solver report that no allocation is possible.
- After the solver, the strategy checks that the expected return is not more than the tolerance below the target. If it is, the run fails with `optimization_failed`.
- The strategy adds "Target return: at least <target>." to the assumptions.

## Target risk

`TargetRiskStrategy` finds the allocation with the highest expected return whose volatility is at most the target. It solves problem 7.2 in Palomar, *Portfolio Optimization*, section 7.1.2:

maximize μᵀw, with ‖Fᵀw‖ ≤ target volatility, "the weights add up to 1" and `weight_constraints`. F is a factor of the covariance matrix (F Fᵀ = Σ), so ‖Fᵀw‖ is the volatility of w.

- The rule is "at most the target". A target at or above the volatility of the highest-return allocation gives that allocation.
- `psd_wrap` does not work in a constraint. For a constraint, CVXPY makes its own factor of the matrix, and this step rejects some matrices that validation accepts, also with `psd_wrap` (for example, a matrix with a smallest eigenvalue of -1e-8). Thus the strategy makes F from the eigenvalues and eigenvectors of Σ, with negative eigenvalues set to 0. Validation permits these eigenvalues only down to -tolerance. When they are set to 0, the risk of an allocation can only increase. Thus a result is never above the target.
- The lowest volatility under the rules is the volatility of the minimum-variance allocation. The strategy gets it from `MinimumVarianceStrategy`. If the target is more than the tolerance below it, `check_target_volatility_reachable` fails the run with `unreachable_target`. The message suggests the lowest volatility, rounded up to 0.1%. If a weight of the minimum-variance allocation is at `max_weight`, the message also says that a larger maximum weight can help.
- If the target is not more than the tolerance above the lowest volatility, the strategy gives the minimum-variance allocation. At the lowest volatility, only one allocation follows the rules, and the solver cannot solve the problem reliably: in a test at exactly the lowest volatility, 145 of 200 problems failed. With this rule, no problem failed from 5e-6 below to 1e-3 above the lowest volatility (200 problems for each value).
- After the solver, the strategy checks that the volatility (with the original Σ) is not more than the tolerance above the target. If it is, the run fails with `optimization_failed`.
- The strategy adds "Target volatility: at most <target>." to the assumptions.

## Minimum history

Too few daily returns give an unreliable covariance matrix. The optimizer then gives weights that look exact but are mostly noise. Thus `OptimizationService` needs this number of daily returns that all stocks share:

required = max(`min_return_observations`, `min_return_observations_per_stock` x number of stocks)

The values are in `Settings`: **60** and **10**. With fewer returns, the run fails with `insufficient_history`.

Why these values:

- Coqueret and Milhau (EDHEC, 2013, "Estimating Covariance Matrices for Portfolio Optimization") give 3 returns per stock as the minimum for portfolio optimization, from Pantaleo et al. (2011).
- We tested the values manually with the daily returns of 20 S&P 500 stocks from 2005 to 2022, long-only weights and a 45% cap. Each test used 5 years of returns as the true values, took a sample of T days from them, and compared the result with the result from the true covariance.
- With 3 returns per stock, the portfolio was about 9% riskier than the best portfolio, and the risk that the app showed was more than 20% too low. With 10 returns per stock, these errors were about 4% and 10% for 5, 10 and 20 stocks.
- For small portfolios, 10 per stock is too few (20 returns for 2 stocks). The minimum of 60 is a rough value from the same manual tests and a practical value: about 12 weeks of trading days. With 60 returns, a 5-stock portfolio had errors of about 4% and 8%.
- The minimum protects only the covariance matrix. It does not make the expected returns reliable. The error of a yearly mean return is about volatility / √(number of years). More days in the same period do not make it smaller (Merton, 1980). Max Sharpe stays sensitive to expected returns (refer to "Maximum Sharpe ratio").
- We also tested Ledoit-Wolf shrinkage of the covariance matrix. With long-only weights, it did not decrease the risk out of sample, so the optimizer uses the sample covariance.

## Tolerance

All checks of calculated values use one absolute tolerance: **1e-5**. Each check gets the tolerance as a parameter. The optimization service gets the value from `Settings`. Values that are not calculated (counts, dates, `max_weight`) are compared exactly.

| Check | Rule |
| --- | --- |
| Covariance is symmetric | No difference is more than the tolerance (`rtol=0`) |
| Covariance is valid | The smallest eigenvalue is not less than -tolerance |
| Rules are feasible | Number of stocks x `max_weight` is not less than 1 - tolerance |
| Can beat the risk-free rate | The highest expected return under the rules is more than the risk-free rate + tolerance |
| Target return can be reached | The target return is not more than the highest expected return under the rules + tolerance |
| Target return is met | The expected return of the result is not less than the target return - tolerance |
| Target volatility can be reached | The target volatility is not less than the lowest volatility under the rules - tolerance |
| Target volatility near the lowest volatility | A target not more than the lowest volatility + tolerance gives the minimum-variance allocation |
| Target volatility is met | The volatility of the result is not more than the target volatility + tolerance |
| Solver noise | Weights nearer to 0 than the tolerance become 0 |
| Weights follow the rules | Sum within the tolerance of 1, no weight below -tolerance, no weight above `max_weight` + tolerance |

Why 1e-5:

- The tolerance must be larger than the errors of the solver. In 600 random problems (minimum variance and max Sharpe, 2 to 50 stocks), the largest CLARABEL error was 8.9e-7. Thus 1e-5 is more than 10 times the largest error. In this test, no correct result was rejected.
- The tolerance also removes solver noise. CLARABEL often gives a very small weight to a stock that should get 0. In the same test, 423 of the 600 results had such weights, and the largest was 8.8e-6. The tolerance changes these weights to 0. With a smaller tolerance, for example 1e-6, some of these weights would stay as very small positions.
- 1e-5 is 0.001% of the money. It is smaller than the last digit of a weight such as 12.34%.
- Yearly variances are about 0.01 to 0.1, so 1e-5 is 0.1% of a value or less. A covariance estimate from 5 years of daily data has an error of about 4% or more.
- The tolerance is correct only for yearly values. Daily values are about 252 times smaller, and 1e-5 is too large for them.

## Error mapping

| Result | Code | HTTP |
| --- | --- | --- |
| The request has a value of the wrong type or range, NaN or Infinity (for example, `max_weight` above 1) | `invalid_request` | 422 |
| The stocks share fewer daily returns than the minimum (refer to "Minimum history") | `insufficient_history` | 422 |
| The inputs do not agree (duplicate tickers, dates, sizes, missing values, bad covariance matrix), or a target strategy has no target | `invalid_optimization_input` | 422 |
| `max_weight` is too small for the number of stocks | `infeasible_allocation_rules` | 422 |
| Max Sharpe only: no allocation under the rules beats the risk-free rate | `no_positive_excess_return` | 422 |
| Target strategies only: no allocation under the rules reaches the target | `unreachable_target` | 422 |
| Solver error, status is not `optimal`, the weights break a rule, or the result does not meet the target | `optimization_failed` | 422 |

## Add a new strategy

1. Make a subclass of `OptimizationStrategy` in `backend/app/optimization/`. Give it a `name`.
2. Get the tolerance and the solver through the constructor.
3. In `compute_weights`, call `check_rules_feasible`. Give the solver one size rule plus `weight_constraints`, and use `psd_wrap` (in a constraint, use a factor of the matrix; refer to "Target risk"). Then call `_solve` and `_clean_and_check`.
4. Return the weights in ticker order.
5. Add the class to `STRATEGIES` in `test_mean_variance.py`. Then the shared tests also run for the new strategy.
6. Add an instance to the list in `create_optimization_service` (`service.py`). The service finds each strategy by its `name`, so the request must send this exact name.
7. Add an option with the same `name` to the strategy menu in `PortfolioSetupPage.tsx`.
