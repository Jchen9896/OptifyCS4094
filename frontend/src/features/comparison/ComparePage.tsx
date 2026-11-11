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
  a: { label: 'Side A', color: 'var(--chart-2)' },
  b: { label: 'Side B', color: 'var(--chart-1)' },
} satisfies ChartConfig

const riskConfig = {
  a: { label: 'Side A', color: 'var(--chart-2)' },
  b: { label: 'Side B', color: 'var(--chart-1)' },
} satisfies ChartConfig

type DistributionMode = 'optimized' | 'original'

type SideSelection = {
  runId: string
  mode: DistributionMode
}

type CompareSide = {
  runId: string
  mode: DistributionMode
  label: string
  strategy: string
  periodStart: string
  periodEnd: string
  expectedReturn: number
  volatility: number
  sharpeRatio: number
  weights: Record<string, number>
  equityKey: 'current_value' | 'optimized_value'
  equityCurve: OptimizationRunDetail['result']['equity_curve']
  hasOriginal: boolean
}

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

function formatRunWhen(run: OptimizationRunSummary): string {
  return new Date(run.created_at).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function encodeSelection(selection: SideSelection): string {
  return `${selection.runId}::${selection.mode}`
}

function parseSelection(value: string | null | undefined): SideSelection | null {
  if (!value) return null
  const [runId, mode] = value.split('::')
  if (!runId || (mode !== 'optimized' && mode !== 'original')) return null
  return { runId, mode }
}

function runHasOriginal(detail: OptimizationRunDetail): boolean {
  const weights = detail.params.current_weights
  return Array.isArray(weights) && weights.length === detail.params.tickers.length
}

function weightsFromCurrent(detail: OptimizationRunDetail): Record<string, number> {
  const list = detail.params.current_weights ?? []
  return Object.fromEntries(
    detail.params.tickers.map((ticker, index) => [ticker, list[index] ?? 0]),
  )
}

function buildCompareSide(detail: OptimizationRunDetail, mode: DistributionMode): CompareSide {
  const hasOriginal = runHasOriginal(detail)
  const useOriginal = mode === 'original' && hasOriginal
  const when = new Date(detail.created_at).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
  return {
    runId: detail.id,
    mode: useOriginal ? 'original' : 'optimized',
    label: useOriginal
      ? `Original · ${when} · ${detail.result.period_start} → ${detail.result.period_end}`
      : `Optimized · ${when} · ${detail.params.strategy} · ${detail.result.period_start} → ${detail.result.period_end}`,
    strategy: useOriginal ? 'Original allocation' : detail.result.strategy,
    periodStart: detail.result.period_start,
    periodEnd: detail.result.period_end,
    expectedReturn: useOriginal
      ? detail.result.current_expected_return
      : detail.result.expected_return,
    volatility: useOriginal ? detail.result.current_volatility : detail.result.volatility,
    sharpeRatio: useOriginal
      ? detail.result.current_sharpe_ratio
      : detail.result.sharpe_ratio,
    weights: useOriginal ? weightsFromCurrent(detail) : detail.result.weights,
    equityKey: useOriginal ? 'current_value' : 'optimized_value',
    equityCurve: detail.result.equity_curve,
    hasOriginal,
  }
}

function defaultSelections(
  rows: OptimizationRunSummary[],
  samePortfolio: boolean,
  side: 'a' | 'b',
): string {
  if (!rows.length) return ''
  if (samePortfolio && rows.length === 1) {
    return encodeSelection({
      runId: rows[0].id,
      mode: side === 'a' ? 'original' : 'optimized',
    })
  }
  if (samePortfolio && side === 'b' && rows.length > 1) {
    return encodeSelection({ runId: rows[1].id, mode: 'optimized' })
  }
  return encodeSelection({ runId: rows[0].id, mode: 'optimized' })
}

function selectionStillValid(value: string, rows: OptimizationRunSummary[]): boolean {
  const parsed = parseSelection(value)
  if (!parsed) return false
  return rows.some((row) => row.id === parsed.runId)
}

export default function ComparePage() {
  const { getToken } = useAuth()
  const { portfolios, activeId } = useActivePortfolio()
  const [portfolioA, setPortfolioA] = useState<string>('')
  const [portfolioB, setPortfolioB] = useState<string>('')
  const [runsA, setRunsA] = useState<OptimizationRunSummary[]>([])
  const [runsB, setRunsB] = useState<OptimizationRunSummary[]>([])
  const [selectionA, setSelectionA] = useState<string>('')
  const [selectionB, setSelectionB] = useState<string>('')
  const [detailA, setDetailA] = useState<OptimizationRunDetail | null>(null)
  const [detailB, setDetailB] = useState<OptimizationRunDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const token = useCallback(async () => {
    const value = await getToken()
    if (!value) throw new Error('Sign in to compare saved runs.')
    return value
  }, [getToken])

  const parsedA = parseSelection(selectionA)
  const parsedB = parseSelection(selectionB)

  useEffect(() => {
    if (!portfolios.length) {
      setPortfolioA('')
      setPortfolioB('')
      return
    }
    const preferred =
      activeId && portfolios.some((row) => row.id === activeId)
        ? activeId
        : portfolios[0].id
    setPortfolioA((current) => current || preferred)
    setPortfolioB((current) => current || preferred)
  }, [portfolios, activeId])

  useEffect(() => {
    if (!portfolioA) {
      setRunsA([])
      setSelectionA('')
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const rows = await listOptimizationRuns(portfolioA, await token())
        if (cancelled) return
        setRunsA(rows)
        setSelectionA((current) =>
          selectionStillValid(current, rows)
            ? current
            : defaultSelections(rows, portfolioA === portfolioB, 'a'),
        )
      } catch (caught) {
        if (!cancelled) {
          setRunsA([])
          setSelectionA('')
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
  }, [portfolioA, portfolioB, token])

  useEffect(() => {
    if (!portfolioB) {
      setRunsB([])
      setSelectionB('')
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const rows = await listOptimizationRuns(portfolioB, await token())
        if (cancelled) return
        setRunsB(rows)
        setSelectionB((current) =>
          selectionStillValid(current, rows)
            ? current
            : defaultSelections(rows, portfolioA === portfolioB, 'b'),
        )
      } catch (caught) {
        if (!cancelled) {
          setRunsB([])
          setSelectionB('')
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
    if (!portfolioA || !parsedA || !portfolioB || !parsedB) {
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
          readOptimizationRun(portfolioA, parsedA.runId, auth),
          readOptimizationRun(portfolioB, parsedB.runId, auth),
        ])
        if (cancelled) return
        setDetailA(a)
        setDetailB(b)
        if (parsedA.mode === 'original' && !runHasOriginal(a)) {
          setSelectionA(encodeSelection({ runId: a.id, mode: 'optimized' }))
        }
        if (parsedB.mode === 'original' && !runHasOriginal(b)) {
          setSelectionB(encodeSelection({ runId: b.id, mode: 'optimized' }))
        }
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
  }, [portfolioA, parsedA?.runId, parsedA?.mode, portfolioB, parsedB?.runId, parsedB?.mode, token])

  const sideA = useMemo(
    () => (detailA && parsedA ? buildCompareSide(detailA, parsedA.mode) : null),
    [detailA, parsedA],
  )
  const sideB = useMemo(
    () => (detailB && parsedB ? buildCompareSide(detailB, parsedB.mode) : null),
    [detailB, parsedB],
  )

  const periodAligned = Boolean(
    sideA &&
      sideB &&
      sideA.periodStart === sideB.periodStart &&
      sideA.periodEnd === sideB.periodEnd,
  )

  const metrics = useMemo(() => {
    if (!sideA || !sideB) return []
    return [
      {
        label: 'Annualized return',
        explanation: 'Expected yearly return for the selected distribution',
        a: sideA.expectedReturn,
        b: sideB.expectedReturn,
        asPercent: true,
      },
      {
        label: 'Annualized volatility',
        explanation: 'Yearly standard deviation of returns for the selected distribution',
        a: sideA.volatility,
        b: sideB.volatility,
        asPercent: true,
      },
      {
        label: 'Sharpe ratio',
        explanation: 'Return per unit of risk after the risk-free rate',
        a: sideA.sharpeRatio,
        b: sideB.sharpeRatio,
        asPercent: false,
      },
    ]
  }, [sideA, sideB])

  const weightRows = useMemo(() => {
    if (!sideA || !sideB) return []
    const symbols = Array.from(
      new Set([...Object.keys(sideA.weights), ...Object.keys(sideB.weights)]),
    ).sort()
    return symbols.map((symbol) => ({
      symbol,
      a: sideA.weights[symbol] ?? 0,
      b: sideB.weights[symbol] ?? 0,
    }))
  }, [sideA, sideB])

  const equityData = useMemo(() => {
    if (!sideA || !sideB || !periodAligned) return []
    const byDate = new Map<string, { date: string; a?: number; b?: number }>()
    for (const point of sideA.equityCurve) {
      byDate.set(point.date, { date: point.date, a: point[sideA.equityKey] })
    }
    for (const point of sideB.equityCurve) {
      const row = byDate.get(point.date) ?? { date: point.date }
      row.b = point[sideB.equityKey]
      byDate.set(point.date, row)
    }
    return Array.from(byDate.values()).sort((left, right) => left.date.localeCompare(right.date))
  }, [sideA, sideB, periodAligned])

  const riskPoints = useMemo(() => {
    if (!sideA || !sideB) return { a: [], b: [] }
    return {
      a: [{ x: sideA.volatility * 100, y: sideA.expectedReturn * 100 }],
      b: [{ x: sideB.volatility * 100, y: sideB.expectedReturn * 100 }],
    }
  }, [sideA, sideB])

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
          Place two sides side by side — optimized run weights or the original allocation stored
          with a run. Prefer selections that share the same historical period.
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
              <FieldLabel>Side A</FieldLabel>
              <Select
                value={selectionA}
                onValueChange={(value) => setSelectionA(value ?? '')}
                disabled={!runsA.length}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={runsA.length ? 'Select distribution' : 'No saved runs'} />
                </SelectTrigger>
                <SelectContent>
                  {runsA.flatMap((row) => [
                    <SelectItem
                      key={`${row.id}-original`}
                      value={encodeSelection({ runId: row.id, mode: 'original' })}
                    >
                      Original allocation · {formatRunWhen(row)} · {row.period_start} →{' '}
                      {row.period_end}
                    </SelectItem>,
                    <SelectItem
                      key={`${row.id}-optimized`}
                      value={encodeSelection({ runId: row.id, mode: 'optimized' })}
                    >
                      Optimized · {formatRunWhen(row)} · {row.strategy} · {row.period_start} →{' '}
                      {row.period_end}
                    </SelectItem>,
                  ])}
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel>Side B</FieldLabel>
              <Select
                value={selectionB}
                onValueChange={(value) => setSelectionB(value ?? '')}
                disabled={!runsB.length}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={runsB.length ? 'Select distribution' : 'No saved runs'} />
                </SelectTrigger>
                <SelectContent>
                  {runsB.flatMap((row) => [
                    <SelectItem
                      key={`${row.id}-original`}
                      value={encodeSelection({ runId: row.id, mode: 'original' })}
                    >
                      Original allocation · {formatRunWhen(row)} · {row.period_start} →{' '}
                      {row.period_end}
                    </SelectItem>,
                    <SelectItem
                      key={`${row.id}-optimized`}
                      value={encodeSelection({ runId: row.id, mode: 'optimized' })}
                    >
                      Optimized · {formatRunWhen(row)} · {row.strategy} · {row.period_start} →{' '}
                      {row.period_end}
                    </SelectItem>,
                  ])}
                </SelectContent>
              </Select>
            </Field>
          </div>
          {sideA && sideB ? (
            <div className="rounded-lg border border-border bg-muted/40 px-3 py-3 text-sm text-muted-foreground">
              <p className="font-medium text-foreground">Historical period</p>
              {periodAligned ? (
                <p className="mt-1">
                  Shared period {sideA.periodStart} → {sideA.periodEnd} · Daily adjusted closes
                </p>
              ) : (
                <p className="mt-1 text-amber-700 dark:text-amber-400">
                  Periods differ. Side A: {sideA.periodStart} → {sideA.periodEnd}. Side B:{' '}
                  {sideB.periodStart} → {sideB.periodEnd}. Metrics stay side by side; equity overlay
                  needs a shared period.
                </p>
              )}
              <p className="mt-2 text-xs">
                {portfolioName(portfolioA)} ({sideA.strategy}) vs {portfolioName(portfolioB)} (
                {sideB.strategy})
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-border bg-muted/40 px-3 py-3 text-sm text-muted-foreground">
              {loading
                ? 'Loading selected sides…'
                : 'Select two sides. Use Original allocation to compare against holdings stored with a run, or Optimized for the solver result.'}
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {sideA && sideB && (
        <>
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle>Aligned metric comparison</CardTitle>
                  <CardDescription>
                    Expected return, volatility, and Sharpe for each selected distribution
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
                    <TableHead>Side A</TableHead>
                    <TableHead>Side B</TableHead>
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
                    ? 'Equity curves for the selected distributions on the shared period'
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
                    Choose two sides with the same period start and end to overlay capital paths.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Asset-level weights</CardTitle>
              <CardDescription>
                {sideA.mode === 'original' || sideB.mode === 'original'
                  ? 'Original and/or optimized weights from the selected sides'
                  : 'Optimized weights from each selected run'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Side A</TableHead>
                    <TableHead>Side B</TableHead>
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
