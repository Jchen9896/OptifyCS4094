# Decision 005 — Portfolio optimizer

Calculate portfolio weights with a subclass of `OptimizationStrategy` in `backend/app/optimization/base.py`. Use **CVXPY** to solve the optimization problem. The strategies are in `mean_variance.py`:

| Strategy | `name` | Goal |
| --- | --- | --- |
| `MinimumVarianceStrategy` | `min_variance` | The lowest risk (variance) |
| `MaxSharpeStrategy` | `max_sharpe` | The highest Sharpe ratio: (expected return - risk-free rate) / volatility |

## Rules

- `validate_optimizer_input` checks the inputs before a strategy gets them. A strategy does not check them again.
- Every strategy gets the same four inputs: `expected_returns`, `covariance`, `max_weight` and `risk_free_rate`. A strategy ignores the inputs that it does not need. The inputs have no default values, so a missing input causes an error immediately. The service changes optional user inputs to real values (for example, the risk-free rate from `Settings`) before it calls a strategy.
- `expected_returns`, `covariance` and `risk_free_rate` are yearly (annualized) values. To change daily values to yearly values, multiply them by 252.
- All strategies follow the allocation rules: the weights add up to 1, no weight is negative (long only), and no weight is above `max_weight`.
- A strategy calls `check_rules_feasible` before it solves.
- `weight_constraints` gives the solver the rules that do not depend on the size of the weights: no weight is negative, and no weight is more than `max_weight` of the total. Each strategy adds one rule that sets the size. Minimum variance uses "the weights add up to 1". Max Sharpe uses "the excess return is 1".
- A strategy gives the covariance matrix to CVXPY through `cp.psd_wrap`. Validation is the only check of the matrix. Without `psd_wrap`, CVXPY does its own stricter check (smallest eigenvalue not below about -1e-10) and can reject a matrix that validation accepted.
- No solver is named, so CVXPY uses its default. For both strategies, the default is OSQP. CLARABEL is also installed and is more accurate. If OSQP fails too often, use `problem.solve(solver="CLARABEL")` in `_solve`.
- `_solve` accepts only the status `optimal`. `optimal_inaccurate` and all other statuses fail.
- `_clean_and_check` calls `clean_weights` and then `find_rule_violations`. If a weight breaks a rule, the run fails.

## Maximum Sharpe ratio

The Sharpe ratio is a ratio, so CVXPY cannot maximize it directly. `MaxSharpeStrategy` uses the Schaible transform (Palomar, *Portfolio Optimization*, section 7.2):

1. The Sharpe ratio does not change when all weights are multiplied by the same positive number.
2. Thus, the strategy solves for scaled weights whose excess return is exactly 1. Then the Sharpe ratio is 1 / (volatility of the scaled weights), and the highest Sharpe ratio has the lowest risk.
3. The solver minimizes the risk of the scaled weights with the rules "excess return is 1" and `weight_constraints`.
4. The strategy divides the scaled weights by their total to get the real weights.

This works only if an allocation under the rules has an expected return above the risk-free rate. `check_can_beat_risk_free_rate` checks this before the solver. It puts as much money as `max_weight` permits in the stocks with the highest expected returns first. If the result is not above the risk-free rate, the run fails.

Known limit: max Sharpe is very sensitive to the expected returns (Palomar, section 7.5). Small errors in the expected returns can move most of the money into one or two stocks. A `max_weight` cap decreases this problem.

## Tolerance

All checks of calculated values use one absolute tolerance: **1e-5**. Each check gets the tolerance as a parameter. The optimization service will get the value from `Settings`. Values that are not calculated (counts, dates, `max_weight`) are compared exactly.

| Check | Rule |
| --- | --- |
| Covariance is symmetric | No difference is more than the tolerance (`rtol=0`) |
| Covariance is valid | The smallest eigenvalue is not less than -tolerance |
| Rules are feasible | Number of stocks x `max_weight` is not less than 1 - tolerance |
| Can beat the risk-free rate | The highest expected return under the rules is more than the risk-free rate + tolerance |
| Solver noise | Weights nearer to 0 than the tolerance become 0 |
| Weights follow the rules | Sum within the tolerance of 1, no weight below -tolerance, no weight above `max_weight` + tolerance |

Why 1e-5:

- CVXPY sets the accuracy target of OSQP to 1e-5 (CVXPY 1.9.3; the OSQP default is 1e-3). A smaller tolerance rejects results that the solver accepts. In a test of 300 random problems, the largest solver error was 6.6e-6. With a tolerance of 1e-6, 2 of the 300 problems failed. With 1e-5, no problem failed for either strategy.
- 1e-5 is 0.001% of the money. It is smaller than the last digit of a weight such as 12.34%.
- Yearly variances are about 0.01 to 0.1, so 1e-5 is 0.1% of a value or less. A covariance estimate from 5 years of daily data has an error of about 4% or more.
- The tolerance is correct only for yearly values. Daily values are about 252 times smaller, and 1e-5 is too large for them.

Known limit: the OSQP stop rule permits errors of up to about 2e-5. Thus, in rare cases, OSQP can give `optimal` with weights that our check rejects. The user then gets `optimization_failed`, not incorrect weights. If this occurs frequently, use CLARABEL.

## Error mapping

| Result | Code | HTTP |
| --- | --- | --- |
| The inputs do not agree (duplicate tickers, dates, sizes, missing values, bad covariance matrix) | `invalid_optimization_input` | 422 |
| `max_weight` is too small for the number of stocks | `infeasible_allocation_rules` | 422 |
| Max Sharpe only: no allocation under the rules beats the risk-free rate | `no_positive_excess_return` | 422 |
| Solver error, status is not `optimal`, or the weights break a rule | `optimization_failed` | 422 |

## Add a new strategy

1. Make a subclass of `OptimizationStrategy` in `backend/app/optimization/`. Give it a `name`.
2. Get the tolerance through the constructor.
3. In `compute_weights`, call `check_rules_feasible`. Give the solver one size rule plus `weight_constraints`, and use `psd_wrap`. Then call `_solve` and `_clean_and_check`.
4. Return the weights in ticker order.
5. Add the class to `STRATEGIES` in `test_mean_variance.py`. Then the shared tests also run for the new strategy.
