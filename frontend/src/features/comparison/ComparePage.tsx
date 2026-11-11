import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '@clerk/react'
import { Link } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  Scatter,
  ScatterChart,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
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
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { Field, FieldLabel } from '@/components/ui/field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ApiError } from '@/lib/apiClient'
import { formatPercent, formatWeight } from '@/lib/formatters.ts'
import {
  listOptimizationRuns,
  readOptimizationRun,
  type OptimizationRunDetail,
  type OptimizationRunSummary,
} from '../optimization/optimizationApi.ts'
import { useActivePortfolio } from '../portfolio/ActivePortfolioContext.tsx'

const equityConfig = {
  a: { label: 'Run A', color: 'var(--chart-2)' },
  b: { label: 'Run B', color: 'var(--chart-1)' },
} satisfies ChartConfig

const riskConfig = {
  a: { label: 'Run A', color: 'var(--chart-2)' },
  b: { label: 'Run B', color: 'var(--chart-1)' },
} satisfies ChartConfig

function formatMetric(value: number | undefined, asPercent: boolean): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  return asPercent ? formatPercent(value) : value.toFixed(2)
}

function formatDelta(a: number | undefined, b: number | undefined, asPercent: boolean): string {
  if (
    typeof a !== 'number' ||
    typeof b !== 'number' ||
    !Number.isFinite(a) ||
    !Number.isFinite(b)
  ) {
    return '—'
  }
  const delta = b - a
  const sign = delta > 0 ? '+' : ''
  return asPercent ? `${sign}${(delta * 100).toFixed(2)} pp` : `${sign}${delta.toFixed(2)}`
}

function formatRunLabel(run: OptimizationRunSummary): string {
  const when = new Date(run.created_at).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
  return `${when} · ${run.strategy} · ${run.period_start} → ${run.period_end}`
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

export default function ComparePage() {
  const { getToken } = useAuth()
  const { portfolios, activeId } = useActivePortfolio()
  const [portfolioA, setPortfolioA] = useState<string>('')
  const [portfolioB, setPortfolioB] = useState<string>('')
  const [runsA, setRunsA] = useState<OptimizationRunSummary[]>([])
  const [runsB, setRunsB] = useState<OptimizationRunSummary[]>([])
  const [runIdA, setRunIdA] = useState<string>('')
  const [runIdB, setRunIdB] = useState<string>('')
  const [detailA, setDetailA] = useState<OptimizationRunDetail | null>(null)
  const [detailB, setDetailB] = useState<OptimizationRunDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const token = useCallback(async () => {
    const value = await getToken()
    if (!value) throw new Error('Sign in to compare saved runs.')
    return value
  }, [getToken])

  useEffect(() => {
    if (!portfolios.length) {
      setPortfolioA('')
      setPortfolioB('')
      return
    }
    const preferred = activeId && portfolios.some((row) => row.id === activeId)
      ? activeId
      : portfolios[0].id
    setPortfolioA((current) => current || preferred)
    setPortfolioB((current) => current || preferred)
  }, [portfolios, activeId])

  useEffect(() => {
    if (!portfolioA) {
      setRunsA([])
      setRunIdA('')
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const rows = await listOptimizationRuns(portfolioA, await token())
        if (cancelled) return
        setRunsA(rows)
        setRunIdA((current) =>
          current && rows.some((row) => row.id === current) ? current : rows[0]?.id ?? '',
        )
      } catch (caught) {
        if (!cancelled) {
          setRunsA([])
          setRunIdA('')
          setError(
            caught instanceof ApiError
              ? `${caught.code}: ${caught.message}`
              : caught instanceof Error
                ? caught.message
                : 'Could not load runs for portfolio A.',
          )
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [portfolioA, token])

  useEffect(() => {
    if (!portfolioB) {
      setRunsB([])
      setRunIdB('')
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const rows = await listOptimizationRuns(portfolioB, await token())
        if (cancelled) return
        setRunsB(rows)
        setRunIdB((current) => {
          if (current && rows.some((row) => row.id === current)) return current
          if (portfolioA === portfolioB && rows.length > 1) return rows[1].id
          return rows[0]?.id ?? ''
        })
      } catch (caught) {
        if (!cancelled) {
          setRunsB([])
          setRunIdB('')
          setError(
            caught instanceof ApiError
              ? `${caught.code}: ${caught.message}`
              : caught instanceof Error
                ? caught.message
                : 'Could not load runs for portfolio B.',
          )
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [portfolioB, portfolioA, token])

  useEffect(() => {
    if (!portfolioA || !runIdA || !portfolioB || !runIdB) {
      setDetailA(null)
      setDetailB(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    void (async () => {
      try {
        const auth = await token()
        const [a, b] = await Promise.all([
          readOptimizationRun(portfolioA, runIdA, auth),
          readOptimizationRun(portfolioB, runIdB, auth),
        ])
        if (cancelled) return
        setDetailA(a)
        setDetailB(b)
      } catch (caught) {
        if (!cancelled) {
          setDetailA(null)
          setDetailB(null)
          setError(
            caught instanceof ApiError
              ? `${caught.code}: ${caught.message}`
              : caught instanceof Error
                ? caught.message
                : 'Could not load the selected runs.',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [portfolioA, runIdA, portfolioB, runIdB, token])

  const periodAligned = Boolean(
    detailA &&
      detailB &&
      detailA.result.period_start === detailB.result.period_start &&
      detailA.result.period_end === detailB.result.period_end,
  )

  const metrics = useMemo(() => {
    if (!detailA || !detailB) return []
    return [
      {
        label: 'Annualized return',
        explanation: 'Expected yearly return from the stored optimization result',
        a: detailA.result.expected_return,
        b: detailB.result.expected_return,
        asPercent: true,
      },
      {
        label: 'Annualized volatility',
        explanation: 'Yearly standard deviation of returns from the stored result',
        a: detailA.result.volatility,
        b: detailB.result.volatility,
        asPercent: true,
      },
      {
        label: 'Sharpe ratio',
        explanation: 'Return per unit of risk after the risk-free rate',
        a: detailA.result.sharpe_ratio,
        b: detailB.result.sharpe_ratio,
        asPercent: false,
      },
    ]
  }, [detailA, detailB])

  const weightRows = useMemo(() => {
    if (!detailA || !detailB) return []
    const symbols = Array.from(
      new Set([...Object.keys(detailA.result.weights), ...Object.keys(detailB.result.weights)]),
    ).sort()
    return symbols.map((symbol) => ({
      symbol,
      a: detailA.result.weights[symbol] ?? 0,
      b: detailB.result.weights[symbol] ?? 0,
    }))
  }, [detailA, detailB])

  const equityData = useMemo(() => {
    if (!detailA || !detailB || !periodAligned) return []
    const byDate = new Map<string, { date: string; a?: number; b?: number }>()
    for (const point of detailA.result.equity_curve) {
      byDate.set(point.date, { date: point.date, a: point.optimized_value })
    }
    for (const point of detailB.result.equity_curve) {
      const row = byDate.get(point.date) ?? { date: point.date }
      row.b = point.optimized_value
      byDate.set(point.date, row)
    }
    return Array.from(byDate.values()).sort((left, right) => left.date.localeCompare(right.date))
  }, [detailA, detailB, periodAligned])

  const riskPoints = useMemo(() => {
    if (!detailA || !detailB) return { a: [], b: [] }
    return {
      a: [{ x: detailA.result.volatility * 100, y: detailA.result.expected_return * 100 }],
      b: [{ x: detailB.result.volatility * 100, y: detailB.result.expected_return * 100 }],
    }
  }, [detailA, detailB])

  const portfolioName = (id: string) => portfolios.find((row) => row.id === id)?.name ?? 'Portfolio'

  if (!portfolios.length) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <div>
          <h1 className="font-heading text-2xl font-semibold">Compare portfolios</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Compare uses saved optimization runs. Create a portfolio from the dashboard with New
            portfolio, run analysis once, then return here.
          </p>
        </div>
        <Button asChild>
          <Link to="/">Go to dashboard</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold">Compare portfolios</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Place two saved optimization runs side by side. Prefer runs that share the same
          historical period.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 pt-(--card-spacing)">
          <div className="grid gap-4 md:grid-cols-2">
            <Field>
              <FieldLabel>Portfolio A</FieldLabel>
              <Select value={portfolioA} onValueChange={setPortfolioA}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select portfolio" />
                </SelectTrigger>
                <SelectContent>
                  {portfolios.map((row) => (
                    <SelectItem key={row.id} value={row.id}>
                      {row.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel>Portfolio B</FieldLabel>
              <Select value={portfolioB} onValueChange={setPortfolioB}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select portfolio" />
                </SelectTrigger>
                <SelectContent>
                  {portfolios.map((row) => (
                    <SelectItem key={row.id} value={row.id}>
                      {row.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel>Run A</FieldLabel>
              <Select value={runIdA} onValueChange={setRunIdA} disabled={!runsA.length}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={runsA.length ? 'Select run' : 'No saved runs'} />
                </SelectTrigger>
                <SelectContent>
                  {runsA.map((row) => (
                    <SelectItem key={row.id} value={row.id}>
                      {formatRunLabel(row)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel>Run B</FieldLabel>
              <Select value={runIdB} onValueChange={setRunIdB} disabled={!runsB.length}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={runsB.length ? 'Select run' : 'No saved runs'} />
                </SelectTrigger>
                <SelectContent>
                  {runsB.map((row) => (
                    <SelectItem key={row.id} value={row.id}>
                      {formatRunLabel(row)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>
          {detailA && detailB ? (
            <div className="rounded-lg border border-border bg-muted/40 px-3 py-3 text-sm text-muted-foreground">
              <p className="font-medium text-foreground">Historical period</p>
              {periodAligned ? (
                <p className="mt-1">
                  Shared period {detailA.result.period_start} → {detailA.result.period_end} · Daily
                  adjusted closes
                </p>
              ) : (
                <p className="mt-1 text-amber-700 dark:text-amber-400">
                  Periods differ. Run A: {detailA.result.period_start} → {detailA.result.period_end}.
                  Run B: {detailB.result.period_start} → {detailB.result.period_end}. Metrics stay
                  side by side; equity overlay needs a shared period.
                </p>
              )}
              <p className="mt-2 text-xs">
                {portfolioName(portfolioA)} vs {portfolioName(portfolioB)} · Results from stored
                optimization runs
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-border bg-muted/40 px-3 py-3 text-sm text-muted-foreground">
              {loading
                ? 'Loading selected runs…'
                : 'Select two saved runs. If a portfolio has no runs yet, edit it from the dashboard, run analysis, then return here.'}
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {detailA && detailB && (
        <>
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle>Aligned metric comparison</CardTitle>
                  <CardDescription>
                    Stored expected return, volatility, and Sharpe for each run
                  </CardDescription>
                </div>
                <Badge variant="secondary">{periodAligned ? 'Shared period' : 'Mixed periods'}</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Metric</TableHead>
                    <TableHead>Run A</TableHead>
                    <TableHead>Run B</TableHead>
                    <TableHead>Difference (B − A)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {metrics.map((row) => (
                    <TableRow key={row.label}>
                      <TableCell>
                        <p className="font-medium">{row.label}</p>
                        <p className="text-xs text-muted-foreground">{row.explanation}</p>
                      </TableCell>
                      <TableCell className="text-lg font-semibold">
                        {formatMetric(row.a, row.asPercent)}
                      </TableCell>
                      <TableCell className="text-lg font-semibold">
                        {formatMetric(row.b, row.asPercent)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDelta(row.a, row.b, row.asPercent)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Historical risk-return profile</CardTitle>
                <CardDescription>Volatility vs expected return markers</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={riskConfig} className="aspect-auto h-64 w-full">
                  <ScatterChart margin={{ left: 12, right: 12, top: 8, bottom: 8 }}>
                    <CartesianGrid />
                    <XAxis
                      type="number"
                      dataKey="x"
                      name="Volatility"
                      unit="%"
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      type="number"
                      dataKey="y"
                      name="Return"
                      unit="%"
                      tickLine={false}
                      axisLine={false}
                      width={48}
                    />
                    <ZAxis range={[80, 80]} />
                    <ChartTooltip
                      content={
                        <ChartTooltipContent
                          formatter={(value, name) =>
                            `${name === 'y' ? 'Return' : 'Volatility'}: ${Number(value).toFixed(2)}%`
                          }
                        />
                      }
                    />
                    <ChartLegend content={<ChartLegendContent />} />
                    <Scatter name="a" data={riskPoints.a} fill="var(--color-a)" />
                    <Scatter name="b" data={riskPoints.b} fill="var(--color-b)" />
                  </ScatterChart>
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Historical performance</CardTitle>
                <CardDescription>
                  {periodAligned
                    ? 'Optimized equity curves on the shared period'
                    : 'Overlay available only when periods match'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {periodAligned && equityData.length ? (
                  <ChartContainer config={equityConfig} className="aspect-auto h-64 w-full">
                    <LineChart accessibilityLayer data={equityData} margin={{ left: 12, right: 12 }}>
                      <CartesianGrid vertical={false} />
                      <XAxis
                        dataKey="date"
                        tickLine={false}
                        axisLine={false}
                        minTickGap={32}
                        tickFormatter={(value: string) => value.slice(5)}
                      />
                      <YAxis
                        tickLine={false}
                        axisLine={false}
                        width={72}
                        tickFormatter={(value: number) => formatCurrency(value)}
                      />
                      <ChartTooltip
                        content={
                          <ChartTooltipContent
                            labelFormatter={(value) => String(value)}
                            formatter={(value) => formatCurrency(Number(value))}
                          />
                        }
                      />
                      <ChartLegend content={<ChartLegendContent />} />
                      <Line
                        type="monotone"
                        dataKey="a"
                        stroke="var(--color-a)"
                        strokeWidth={2}
                        dot={false}
                        connectNulls
                      />
                      <Line
                        type="monotone"
                        dataKey="b"
                        stroke="var(--color-b)"
                        strokeWidth={2}
                        dot={false}
                        connectNulls
                      />
                    </LineChart>
                  </ChartContainer>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Choose two runs with the same period start and end to overlay capital paths.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Asset-level weights</CardTitle>
              <CardDescription>Optimized weights from each stored run</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Run A</TableHead>
                    <TableHead>Run B</TableHead>
                    <TableHead>Difference</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {weightRows.map((row) => (
                    <TableRow key={row.symbol}>
                      <TableCell className="font-medium">{row.symbol}</TableCell>
                      <TableCell>{formatWeight(row.a)}</TableCell>
                      <TableCell>{formatWeight(row.b)}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDelta(row.a, row.b, true)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
