import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
import { formatPercent, formatWeight } from '@/lib/formatters.ts'
import { loadLastOptimizationRun } from '../optimization/optimizationApi.ts'
import PortfolioPerformanceCharts from './PortfolioPerformanceCharts.tsx'

export default function DashboardPage() {
  const run = useMemo(() => loadLastOptimizationRun(), [])

  if (!run) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <div>
          <h1 className="font-heading text-2xl font-semibold">Portfolio optimization overview</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            No live optimization run yet. Set up a portfolio, load prices, and run analysis.
          </p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Get started</CardTitle>
            <CardDescription>
              The dashboard shows weights and risk metrics from your last run in this browser
              session.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link to="/setup">Go to portfolio setup</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { result, holdings, portfolioName } = run
  const names = Object.fromEntries(holdings.map((holding) => [holding.symbol, holding.name]))
  const weightRows = Object.entries(result.weights).map(([symbol, weight]) => ({
    symbol,
    name: names[symbol] ?? symbol,
    weight,
  }))
  const currentBySymbol = Object.fromEntries(
    holdings.map((holding) => [holding.symbol, holding.weightPercent / 100]),
  )

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">Portfolio optimization overview</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Review optimized weights and estimated risk and return for the selected historical
            period.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Estimate · {portfolioName} · {result.period_start} – {result.period_end} ·{' '}
            {result.strategy}
          </p>
        </div>
        <Button asChild variant="outline">
          <Link to="/setup">Edit portfolio setup</Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Assets', value: String(weightRows.length), note: 'In optimized set' },
          {
            label: 'Expected return',
            value: formatPercent(result.expected_return),
            note: 'Annualized estimate',
          },
          {
            label: 'Volatility',
            value: formatPercent(result.volatility),
            note: 'Annualized estimate',
          },
          {
            label: 'Sharpe ratio',
            value: result.sharpe_ratio.toFixed(2),
            note: 'Using configured risk-free rate',
          },
        ].map((kpi) => (
          <Card key={kpi.label} size="sm">
            <CardHeader>
              <CardDescription className="text-xs tracking-wide uppercase">{kpi.label}</CardDescription>
              <CardTitle className="text-2xl">{kpi.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">{kpi.note}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {result.equity_curve?.length ? (
        <PortfolioPerformanceCharts
          equityCurve={result.equity_curve}
          initialCapital={result.initial_capital}
          weightRows={weightRows.map((row) => ({
            symbol: row.symbol,
            current: currentBySymbol[row.symbol] ?? 0,
            optimized: row.weight,
          }))}
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Performance charts</CardTitle>
            <CardDescription>
              Re-run analysis from Portfolio setup to load capital and weight charts.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>Optimized weights</CardTitle>
                <CardDescription>Long-only allocation from the last run</CardDescription>
              </div>
              <Badge variant="secondary">Live</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Current</TableHead>
                  <TableHead>Optimized</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {weightRows.map((row) => (
                  <TableRow key={row.symbol}>
                    <TableCell className="font-medium">{row.symbol}</TableCell>
                    <TableCell className="text-muted-foreground">{row.name}</TableCell>
                    <TableCell>{formatWeight(currentBySymbol[row.symbol] ?? 0)}</TableCell>
                    <TableCell>{formatWeight(row.weight)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Assumptions</CardTitle>
            <CardDescription>How this estimate was produced</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
              {result.assumptions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Allocation details</CardTitle>
          <CardDescription>Optimized weights by asset</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {weightRows.map((row) => (
            <div key={row.symbol}>
              <div className="mb-1 flex justify-between text-sm">
                <span>{row.symbol}</span>
                <span className="text-muted-foreground">{formatWeight(row.weight)}</span>
              </div>
              <div className="h-2 rounded bg-muted">
                <div
                  className="h-2 rounded bg-primary"
                  style={{ width: formatWeight(row.weight, 2) }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
