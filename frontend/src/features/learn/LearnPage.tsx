import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const historyWeights = [
  { period: '3 months', weight: 'about 1%' },
  { period: '1 year', weight: 'about 5%' },
  { period: '3 years', weight: 'about 13%' },
  { period: '10 years', weight: 'about 33%' },
]

const decisions = [
  {
    question: 'Why the S&P 500?',
    answer:
      'To know how a stock moves with "the market", we need one price for the whole market. The S&P 500 already weights about 500 large U.S. companies by their size and keeps that up to date. We use SPY, a fund that follows it, so we do not have to build the market ourselves.',
  },
  {
    question: 'Why a fixed 5%?',
    answer:
      'Kroll, a valuation firm, publishes this estimate of the extra yearly return that investors expect from U.S. stocks. If we estimated it from your period instead, it would be too high after good years and below zero after crashes.',
  },
  {
    question: 'Why can I not enter my own predictions?',
    answer:
      'Good predictions are hard, even for professionals. Optify uses the market and your price history as its only inputs, so a guess cannot push your money into a few stocks.',
  },
  {
    question: 'Why does history still count?',
    answer:
      'History is noisy, but it is not useless. It gets more weight when you choose a longer period, because a longer period gives a more reliable average.',
  },
]

const strategies = [
  {
    name: 'Minimum variance',
    goal: 'The lowest risk.',
    detail:
      'It finds the mix with the smallest ups and downs. It does not use expected returns, so the Black–Litterman step does not change its weights.',
    formula: null,
  },
  {
    name: 'Maximum Sharpe ratio',
    goal: 'The best return for each unit of risk.',
    detail:
      'The Sharpe ratio measures how much extra return you get for the risk you take. A higher ratio is better.',
    formula: 'Sharpe ratio = (expected return − risk-free rate) ÷ risk',
  },
  {
    name: 'Target return',
    goal: 'The lowest risk that reaches your return goal.',
    detail:
      'You choose a yearly return. Optify finds the safest mix that is expected to earn at least that much. If no mix can reach it, Optify tells you the highest return that is possible.',
    formula: null,
  },
  {
    name: 'Target risk',
    goal: 'The highest return that stays inside your risk limit.',
    detail:
      'You choose how much risk you accept. Optify finds the mix with the highest expected return that stays at or below that risk. If your limit is too low, Optify tells you the lowest risk that is possible.',
    formula: null,
  },
]

const rules = [
  'Your weights always add up to 100%.',
  'No stock gets a negative weight. Optify never bets against a stock.',
  'No stock gets more than your maximum weight per stock.',
  'Your stocks must share at least 60 trading days of prices, and at least 10 for each stock.',
]

function Formula({ text, meaning }: { text: string; meaning: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/40 px-3 py-3">
      <p className="font-medium text-foreground">{text}</p>
      <p className="mt-1 text-sm text-muted-foreground">{meaning}</p>
    </div>
  )
}

export default function LearnPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold">How Optify builds your portfolio</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Optify does two things. First, it estimates how much each stock can earn in a year.
          Then a strategy uses those estimates to split your money between your stocks.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Step 1: Estimate the returns (Black–Litterman)</CardTitle>
          <CardDescription>How Optify decides what each stock is expected to earn</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <p className="font-medium">The problem with past averages</p>
            <p className="mt-1 text-muted-foreground">
              The easy estimate is a stock's average return in the period you choose. But that
              average is mostly luck. For a typical single stock, one year of history can be off by
              about 30 percentage points either way. A strategy that trusts it puts most of your
              money in the stocks that were lucky, not the stocks that are good.
            </p>
          </div>

          <div className="space-y-2">
            <p className="font-medium">1. Start with a market-based estimate</p>
            <Formula
              text="Starting estimate = risk-free rate + beta × 5%"
              meaning="Beta shows how much a stock moves with the S&P 500. A beta of 1.2 means the stock tends to move 12% when the market moves 10%. 5% is the extra return that investors expect each year for owning stocks. A stock that moves more with the market takes more market risk, so it is expected to earn more."
            />
          </div>

          <div className="space-y-2">
            <p className="font-medium">2. Add a little of your price history</p>
            <Formula
              text="Weight on history = years of history ÷ (years of history + 20)"
              meaning="Optify gives your history more weight when you choose a longer period. The starting estimate counts as about 20 years of data."
            />
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period you choose</TableHead>
                  <TableHead>Weight on your history</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historyWeights.map((row) => (
                  <TableRow key={row.period}>
                    <TableCell>{row.period}</TableCell>
                    <TableCell>{row.weight}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="space-y-3">
            <p className="font-medium">Why it works this way</p>
            {decisions.map((item) => (
              <div key={item.question}>
                <p className="font-medium text-foreground">{item.question}</p>
                <p className="mt-1 text-muted-foreground">{item.answer}</p>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-border bg-muted/40 px-3 py-3">
            <p className="font-medium">What this means for you</p>
            <p className="mt-1 text-muted-foreground">
              In our tests on 22 years of S&P 500 data, the results earned about the same as before.
              But the promised numbers were much closer to what really happened, the money was
              spread over more stocks, and no runs were refused. The returns you see are estimates,
              not guarantees.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Step 2: Choose a strategy</CardTitle>
          <CardDescription>How Optify splits your money with those estimates</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p className="text-muted-foreground">
            "Risk" here means how much your portfolio's value goes up and down in a year. "Expected
            return" is the estimate from step 1.
          </p>
          {strategies.map((strategy) => (
            <div key={strategy.name} className="space-y-2 border-t border-border pt-4">
              <p className="font-medium">{strategy.name}</p>
              <p className="text-foreground">{strategy.goal}</p>
              <p className="text-muted-foreground">{strategy.detail}</p>
              {strategy.formula && (
                <Formula
                  text={strategy.formula}
                  meaning="The risk-free rate is what a very safe investment, such as a U.S. Treasury bill, pays."
                />
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Rules every portfolio follows</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {rules.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
