import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '@clerk/react'
import { Badge } from '@/components/ui/badge'
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
import { ApiError } from '@/lib/apiClient'
import { formatPercent, formatWeight } from '@/lib/formatters.ts'
import {
  clearLastOptimizationRun,
  deleteOptimizationRun,
  listOptimizationRuns,
  loadLastOptimizationRun,
  readOptimizationRun,
  type OptimizationResult,
  type OptimizationRunSummary,
  type StoredOptimizationRun,
} from '../optimization/optimizationApi.ts'
import { useActivePortfolio } from '../portfolio/ActivePortfolioContext.tsx'
import { readPortfolio } from '../portfolio/portfolioApi.ts'
import type { Holding } from '../portfolio/types.ts'
import PortfolioSwitcher from '../portfolio/components/PortfolioSwitcher.tsx'
import RunSwitcher from '../portfolio/components/RunSwitcher.tsx'
import PortfolioPerformanceCharts from './PortfolioPerformanceCharts.tsx'

type DashboardRun = {
  result: OptimizationResult
  holdings: Holding[]
  portfolioName: string
  referencePrices: Record<string, number>
  initialCapital: number
  source: 'saved' | 'session'
  runId?: string
  createdAt?: string
  saveNote?: string | null
}

function formatMetric(value: number | undefined, asPercent: boolean): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '—'
  }
  return asPercent ? formatPercent(value) : value.toFixed(2)
}

function formatDelta(before: number | undefined, after: number, asPercent: boolean): string {
  if (typeof before !== 'number' || !Number.isFinite(before) || !Number.isFinite(after)) {
    return '—'
  }
  const delta = after - before
  const sign = delta > 0 ? '+' : ''
  if (asPercent) {
    return `${sign}${(delta * 100).toFixed(2)} pp`
  }
  return `${sign}${delta.toFixed(2)}`
}

function formatShares(value: number | null): string {
  if (value == null || !Number.isFinite(value) || value <= 0) {
    return '—'
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 })
}

function sharesForWeight(
  weight: number,
  capital: number,
  price: number | undefined,
): number | null {
  if (!(typeof price === 'number' && price > 0 && capital > 0 && Number.isFinite(weight))) {
    return null
  }
  return (weight * capital) / price
}

function fromSession(run: StoredOptimizationRun, portfolioName: string): DashboardRun {
  return {
    result: run.result,
    holdings: run.holdings,
    portfolioName: run.portfolioName || portfolioName,
    referencePrices: run.referencePrices ?? {},
    initialCapital: run.initialCapital ?? run.result.initial_capital,
    source: 'session',
    saveNote: run.saveNote,
  }
}

function holdingsFromParams(
  tickers: string[],
  currentWeights: number[] | null | undefined,
  capital: number,
  prices: Record<string, number>,
  quantityBySymbol: Record<string, number> = {},
): Holding[] {
  return tickers.map((symbol, index) => {
    const weightPercent = Number(((currentWeights?.[index] ?? 0) * 100).toFixed(4))
    const storedQty = quantityBySymbol[symbol]
    const estimated = sharesForWeight(weightPercent / 100, capital, prices[symbol])
    return {
      symbol,
      name: symbol,
      quoteType: null,
      weightPercent,
      quantity:
        typeof storedQty === 'number' && storedQty > 0
          ? storedQty
          : estimated ?? 0,
    }
  })
}

export default function DashboardPage() {
  const { userId, getToken } = useAuth()
  const { activeId, activeLabel } = useActivePortfolio()
  const [runSummaries, setRunSummaries] = useState<OptimizationRunSummary[]>([])
  const [selectedRunId, setSelectedRunId] = useState('')
  const [savedRun, setSavedRun] = useState<DashboardRun | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sessionRun = useMemo(() => {
    const stored = loadLastOptimizationRun(userId ?? null, activeId)
    return stored ? fromSession(stored, activeLabel) : null
  }, [userId, activeId, activeLabel])

  const token = useCallback(async () => {
    const value = await getToken()
    if (!value) throw new Error('Sign in to load saved runs.')
    return value
  }, [getToken])

  useEffect(() => {
    if (!activeId) {
      setRunSummaries([])
      setSelectedRunId('')
      setSavedRun(null)
      setError(null)
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)
    void (async () => {
      try {
        const rows = await listOptimizationRuns(activeId, await token())
        if (cancelled) return
        setRunSummaries(rows)
        setSelectedRunId((current) =>
          current && rows.some((row) => row.id === current) ? current : rows[0]?.id ?? '',
        )
        if (rows.length === 0) {
          setSavedRun(null)
        }
      } catch (caught) {
        if (cancelled) return
        setRunSummaries([])
        setSelectedRunId('')
        setSavedRun(null)
        setError(
          caught instanceof ApiError
            ? `${caught.code}: ${caught.message}`
            : caught instanceof Error
              ? caught.message
              : 'Could not load saved runs.',
        )
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [activeId, token])

  useEffect(() => {
    if (!activeId || !selectedRunId) {
      return
    }
    let cancelled = false
    setLoading(true)
    void (async () => {
      try {
        const auth = await token()
        const [detail, portfolio] = await Promise.all([
          readOptimizationRun(activeId, selectedRunId, auth),
          readPortfolio(auth, activeId).catch(() => null),
        ])
        if (cancelled) return
        const capital =
          detail.params.initial_capital ?? detail.result.initial_capital ?? 0
        const prices = {
          ...(portfolio?.setup?.reference_prices ?? {}),
          ...(detail.params.reference_prices ?? {}),
        }
        const quantityBySymbol = Object.fromEntries(
          (portfolio?.holdings ?? []).map((holding) => [
            holding.symbol,
            Number(holding.quantity),
          ]),
        )
        setSavedRun({
          result: detail.result,
          holdings: holdingsFromParams(
            detail.params.tickers,
            detail.params.current_weights,
            capital,
            prices,
            quantityBySymbol,
          ),
          portfolioName: activeLabel,
          referencePrices: prices,
          initialCapital: capital,
          source: 'saved',
          runId: detail.id,
          createdAt: detail.created_at,
        })
        setError(null)
      } catch (caught) {
        if (cancelled) return
        setSavedRun(null)
        setError(
          caught instanceof ApiError
            ? `${caught.code}: ${caught.message}`
            : caught instanceof Error
              ? caught.message
              : 'Could not load the selected run.',
        )
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [activeId, selectedRunId, activeLabel, token])

  const refreshRuns = useCallback(async () => {
    if (!activeId) return
    setLoading(true)
    setError(null)
    try {
      const rows = await listOptimizationRuns(activeId, await token())
      setRunSummaries(rows)
      setSelectedRunId((current) =>
        current && rows.some((row) => row.id === current) ? current : rows[0]?.id ?? '',
      )
      if (rows.length === 0) setSavedRun(null)
    } catch (caught) {
      setRunSummaries([])
      setSelectedRunId('')
      setSavedRun(null)
      setError(
        caught instanceof ApiError
          ? `${caught.code}: ${caught.message}`
          : caught instanceof Error
            ? caught.message
            : 'Could not load saved runs.',
      )
    } finally {
      setLoading(false)
    }
  }, [activeId, token])

  async function handleDeleteRun(runId: string) {
    if (!activeId) return
    setLoading(true)
    setError(null)
    try {
      await deleteOptimizationRun(activeId, runId, await token())
      clearLastOptimizationRun(userId ?? null, activeId)
      const rows = await listOptimizationRuns(activeId, await token())
      setRunSummaries(rows)
      if (selectedRunId === runId) {
        setSelectedRunId(rows[0]?.id ?? '')
        if (rows.length === 0) setSavedRun(null)
      }
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? `${caught.code}: ${caught.message}`
          : caught instanceof Error
            ? caught.message
            : 'Could not delete the run.',
      )
    } finally {
      setLoading(false)
    }
  }

  // Saved portfolio → persisted run. New portfolio → browser session only.
  const run = activeId ? savedRun : sessionRun

  if (!run) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="font-heading text-2xl font-semibold">Portfolio optimization overview</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              {activeId
                ? loading
                  ? `Loading saved runs for ${activeLabel}…`
                  : `No saved optimization runs for ${activeLabel} yet. Use Edit in the switcher, run analysis on setup, then return here.`
                : `Select a saved portfolio, or use New portfolio to open setup and run analysis.`}
            </p>
            {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
          </div>
          <PortfolioSwitcher label="Portfolio" />
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Portfolio vs run</CardTitle>
            <CardDescription>
              A portfolio stores holdings and setup. Each analysis creates a saved run on that
              portfolio. Compare picks two runs; this dashboard shows one run for the active
              portfolio.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  const { result, holdings, portfolioName, referencePrices = {}, initialCapital, saveNote } = run
  const capital = initialCapital ?? result.initial_capital
  const names = Object.fromEntries(holdings.map((holding) => [holding.symbol, holding.name]))
  const currentBySymbol = Object.fromEntries(
    holdings.map((holding) => [holding.symbol, holding.weightPercent / 100]),
  )
  const currentQtyBySymbol = Object.fromEntries(
    holdings.map((holding) => [holding.symbol, holding.quantity ?? 0]),
  )
  const weightRows = Object.entries(result.weights).map(([symbol, weight]) => {
    const price = referencePrices[symbol]
    const currentWeight = currentBySymbol[symbol] ?? 0
    const storedCurrentQty = currentQtyBySymbol[symbol]
    const currentQty =
      typeof storedCurrentQty === 'number' && storedCurrentQty > 0
        ? storedCurrentQty
        : sharesForWeight(currentWeight, capital, price)
    const optimizedQty = sharesForWeight(weight, capital, price)
    return {
      symbol,
      name: names[symbol] ?? symbol,
      weight,
      currentWeight,
      currentQty,
      optimizedQty,
    }
  })

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">Portfolio optimization overview</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Review one optimization run for the active portfolio. Compare can place two saved runs
            side by side.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            {run.source === 'saved' ? 'Saved run' : 'Session run'} · {portfolioName} ·{' '}
            {result.period_start} – {result.period_end} · {result.strategy}
            {run.createdAt
              ? ` · ${new Date(run.createdAt).toLocaleString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}`
              : ''}
          </p>
          {saveNote && <p className="mt-2 text-sm text-muted-foreground">{saveNote}</p>}
          {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
        </div>
        <div className="w-full min-w-[20rem] max-w-xl shrink-0 space-y-3">
          <PortfolioSwitcher
            label="Portfolio"
            className="w-full max-w-none sm:items-stretch"
          />
          {activeId && runSummaries.length > 0 && (
            <RunSwitcher
              label="Run"
              runs={runSummaries}
              selectedRunId={selectedRunId}
              busy={loading}
              onSelect={setSelectedRunId}
              onDelete={handleDeleteRun}
              onOpen={() => void refreshRuns()}
              className="w-full max-w-none sm:items-stretch"
            />
          )}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card size="sm">
          <CardHeader>
            <CardDescription className="text-xs tracking-wide uppercase">Assets</CardDescription>
            <CardTitle className="text-2xl">{weightRows.length}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Holdings in the run</p>
          </CardContent>
        </Card>
        {(
          [
            {
              label: 'Expected return',
              before: result.current_expected_return,
              after: result.expected_return,
              note: 'Annualized estimate',
              asPercent: true,
            },
            {
              label: 'Volatility',
              before: result.current_volatility,
              after: result.volatility,
              note: 'Annualized estimate',
              asPercent: true,
            },
            {
              label: 'Sharpe ratio',
              before: result.current_sharpe_ratio,
              after: result.sharpe_ratio,
              note: 'Using configured risk-free rate',
              asPercent: false,
            },
          ] as const
        ).map((kpi) => (
          <Card key={kpi.label} size="sm">
            <CardHeader>
              <CardDescription className="text-xs tracking-wide uppercase">{kpi.label}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-muted-foreground">Current</p>
                  <p className="text-xl font-semibold tabular-nums">
                    {formatMetric(kpi.before, kpi.asPercent)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Optimized</p>
                  <p className="text-xl font-semibold tabular-nums">
                    {formatMetric(kpi.after, kpi.asPercent)}
                  </p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Delta {formatDelta(kpi.before, kpi.after, kpi.asPercent)} · {kpi.note}
              </p>
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
            current: row.currentWeight,
            optimized: row.weight,
          }))}
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Performance charts</CardTitle>
            <CardDescription>
              This saved run has no equity curve. Edit the portfolio and run analysis again.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>Optimized allocation</CardTitle>
                <CardDescription>Weights from the selected run</CardDescription>
              </div>
              <Badge variant="secondary">{run.source === 'saved' ? 'Saved' : 'Session'}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Current wt</TableHead>
                  <TableHead>Opt. wt</TableHead>
                  <TableHead>Current qty</TableHead>
                  <TableHead>Opt. qty</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {weightRows.map((row) => (
                  <TableRow key={row.symbol}>
                    <TableCell className="font-medium">{row.symbol}</TableCell>
                    <TableCell className="text-muted-foreground">{row.name}</TableCell>
                    <TableCell>{formatWeight(row.currentWeight)}</TableCell>
                    <TableCell>{formatWeight(row.weight)}</TableCell>
                    <TableCell>{formatShares(row.currentQty)}</TableCell>
                    <TableCell>{formatShares(row.optimizedQty)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Historical asset returns</CardTitle>
            <CardDescription>
              Annualized return and volatility by ticker for {result.period_start} –{' '}
              {result.period_end}. Unavailable values show as —.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {(result.asset_stats?.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">
                No per-ticker stats on this run. Re-run analysis to populate them.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Ann. return</TableHead>
                    <TableHead>Ann. volatility</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.asset_stats?.map((row) => (
                    <TableRow key={row.symbol}>
                      <TableCell className="font-medium">{row.symbol}</TableCell>
                      <TableCell className="tabular-nums">
                        {row.annualized_return == null
                          ? '—'
                          : formatPercent(row.annualized_return)}
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {row.annualized_volatility == null
                          ? '—'
                          : formatPercent(row.annualized_volatility)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
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
