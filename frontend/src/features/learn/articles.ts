export type LearnArticle = {
  slug: string
  title: string
  summary: string
  category: 'Concepts' | 'How to use'
  minutes: number
  sections: { heading: string; paragraphs: string[] }[]
}

export const LEARN_ARTICLES: LearnArticle[] = [
  {
    slug: 'getting-started',
    title: 'Getting started with Optify',
    summary: 'Sign in, build a portfolio, run analysis, and review results on the dashboard.',
    category: 'How to use',
    minutes: 4,
    sections: [
      {
        heading: 'What Optify does',
        paragraphs: [
          'Optify helps you set up a portfolio of stocks or funds, choose a historical period, and run an optimization strategy. The result shows suggested weights plus estimated return, risk, and Sharpe ratio for that period.',
          'Results are historical estimates for the dates you chose. They are not forecasts or guaranteed outcomes.',
        ],
      },
      {
        heading: 'Suggested first path',
        paragraphs: [
          'Open Portfolio manager. Name the portfolio, set an initial value, add at least two holdings, make weights total 100%, and save. Then open Portfolio analysis to choose a start and end date, pick a strategy, and run.',
          'When you are signed in, Optify saves the portfolio and stores each optimization run so you can reopen results later and use Compare.',
        ],
      },
      {
        heading: 'Where to go next',
        paragraphs: [
          'Use the Dashboard to review the latest run for the active portfolio. Use Compare to place two saved runs side by side. Use Learn whenever a metric or strategy needs a clearer explanation.',
        ],
      },
    ],
  },
  {
    slug: 'portfolio-setup',
    title: 'Building a portfolio on Setup',
    summary: 'Holdings, weights, prices, dates, and the inputs that feed analysis.',
    category: 'How to use',
    minutes: 5,
    sections: [
      {
        heading: 'Holdings and weights',
        paragraphs: [
          'Search for tickers and add them to the table. Each holding needs a weight. Optify keeps share quantities in step with your initial portfolio value and the reference prices for the period.',
          'Analysis needs at least two assets and weights that total 100%.',
        ],
      },
      {
        heading: 'Historical period',
        paragraphs: [
          'The start and end dates define which stored daily prices Optify uses. Longer periods usually give more observations, but the range must still be covered by available price history.',
          'When you run analysis, Optify loads missing prices for that window before it optimizes.',
        ],
      },
      {
        heading: 'Saving while signed in',
        paragraphs: [
          'A new portfolio name is saved to your account on a successful run. The dashboard portfolio switcher lists those saved portfolios. Switching on the dashboard only changes which portfolio you are viewing; open Setup when you need to edit holdings or run again.',
        ],
      },
    ],
  },
  {
    slug: 'optimization-strategies',
    title: 'Choosing an optimization strategy',
    summary: 'Minimum variance, maximum Sharpe, target return, and target risk.',
    category: 'Concepts',
    minutes: 6,
    sections: [
      {
        heading: 'Minimum variance',
        paragraphs: [
          'This strategy looks for the allocation with the lowest estimated volatility under your weight rules. It does not chase higher expected return.',
        ],
      },
      {
        heading: 'Maximum Sharpe ratio',
        paragraphs: [
          'Sharpe ratio measures estimated excess return per unit of risk after the risk-free rate. Maximum Sharpe looks for the allocation with the best risk-adjusted estimate under your rules.',
          'You must enter an assumed annual risk-free rate for this strategy.',
        ],
      },
      {
        heading: 'Target return',
        paragraphs: [
          'Enter a target annual return. Optify looks for the lowest-risk allocation that still reaches that expected return under the weight rules. If no feasible allocation can reach the target, the run fails with a clear error.',
        ],
      },
      {
        heading: 'Target risk',
        paragraphs: [
          'Enter a target annual volatility. Optify looks for the highest-return allocation that stays at or below that risk under the weight rules. A target below the lowest feasible volatility also fails with a clear error.',
        ],
      },
      {
        heading: 'Shared constraints',
        paragraphs: [
          'All strategies respect non-negative weights that sum to 100% and your maximum weight per asset. A maximum weight that is too small for the number of holdings can make the problem infeasible.',
        ],
      },
    ],
  },
  {
    slug: 'risk-return-sharpe',
    title: 'Risk, return, and Sharpe ratio',
    summary: 'What the dashboard metrics mean and how to read them carefully.',
    category: 'Concepts',
    minutes: 5,
    sections: [
      {
        heading: 'Expected return',
        paragraphs: [
          'Optify reports an annualized expected return estimated from the historical period and the chosen method. Treat it as a period-based estimate, not a promise of future performance.',
        ],
      },
      {
        heading: 'Volatility',
        paragraphs: [
          'Volatility is the annualized standard deviation of returns. Higher volatility means larger typical swings. Minimum-variance and target-return strategies care about this number directly.',
        ],
      },
      {
        heading: 'Sharpe ratio',
        paragraphs: [
          'Sharpe ratio divides excess return (return minus the risk-free rate) by volatility. A higher Sharpe means more estimated excess return for each unit of risk in that historical window.',
          'Comparing Sharpe values only makes sense when the period, assumptions, and universe are aligned.',
        ],
      },
    ],
  },
  {
    slug: 'reading-the-dashboard',
    title: 'Reading the dashboard',
    summary: 'Weights, metrics, and capital paths after a successful analysis.',
    category: 'How to use',
    minutes: 4,
    sections: [
      {
        heading: 'Current vs optimized',
        paragraphs: [
          'The dashboard compares your current weights with the optimized weights from the latest run in this browser session for the active portfolio. Charts show how capital would have moved on shared trading days under both sets of weights.',
        ],
      },
      {
        heading: 'Assumptions',
        paragraphs: [
          'Each result includes assumption lines such as strategy name, period, and targets. Read those lines before you act on a difference between current and optimized allocations.',
        ],
      },
      {
        heading: 'If the dashboard is empty',
        paragraphs: [
          'Run analysis from Setup for the selected portfolio. The dashboard uses the last run stored for that portfolio in this browser. Saved run history for Compare is separate and lives in your account.',
        ],
      },
    ],
  },
  {
    slug: 'comparing-runs',
    title: 'Comparing saved runs fairly',
    summary: 'How Compare uses persisted optimization runs and why periods matter.',
    category: 'How to use',
    minutes: 4,
    sections: [
      {
        heading: 'What Compare shows',
        paragraphs: [
          'Compare lets you pick two saved optimization runs from portfolios you own. It shows metrics, weights, risk-return markers, and an equity overlay when the periods match.',
        ],
      },
      {
        heading: 'Shared historical period',
        paragraphs: [
          'A fair comparison uses the same start and end dates. When periods differ, Optify still shows side-by-side metrics, but it warns you and skips the equity overlay so it does not invent a shared history.',
          'If you need a clean comparison, run analysis again on both portfolios with the same dates, then select those new runs.',
        ],
      },
      {
        heading: 'Creating history',
        paragraphs: [
          'Each successful analysis on a saved portfolio writes an optimization run. Run more than once with different strategies or dates to build a history you can compare.',
        ],
      },
    ],
  },
  {
    slug: 'historical-estimates',
    title: 'What historical estimates can and cannot tell you',
    summary: 'Limits of backtested optimization and how Optify frames results.',
    category: 'Concepts',
    minutes: 4,
    sections: [
      {
        heading: 'In-sample estimates',
        paragraphs: [
          'Optify optimizes and reports metrics on the same historical window you selected. That helps you study how a rule would have behaved on past prices, but it can look better than live results because the rule is fitted to that sample.',
        ],
      },
      {
        heading: 'Data and universe limits',
        paragraphs: [
          'Only tickers and date ranges with usable stored prices can run. Changing the universe, maximum weight, or risk-free rate can change the answer even when the dates stay the same.',
        ],
      },
      {
        heading: 'How Optify phrases outcomes',
        paragraphs: [
          'Screens label results as estimates for a chosen period. Use them to understand trade-offs and process, not as investment advice.',
        ],
      },
    ],
  },
]

export function getLearnArticle(slug: string): LearnArticle | undefined {
  return LEARN_ARTICLES.find((article) => article.slug === slug)
}
