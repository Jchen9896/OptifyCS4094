import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '@clerk/react'
import { Link, useNavigate } from 'react-router-dom'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ApiError } from '@/lib/apiClient'
import HistoryPeriodPanel from '../history-period/HistoryPeriodPanel.tsx'
import { ensureHoldingsPrices } from '../history-period/historyApi.ts'
import {
  clearLastOptimizationRun,
  deleteOptimizationRun,
  listOptimizationRuns,
  readOptimizationRun,
  runOptimization,
  saveLastOptimizationRun,
  saveOptimizationRun,
  type OptimizationRunParams,
  type OptimizationRunSummary,
} from '../optimization/optimizationApi.ts'
import { useActivePortfolio } from './ActivePortfolioContext.tsx'
import PortfolioSwitcher from './components/PortfolioSwitcher.tsx'
import RunSwitcher from './components/RunSwitcher.tsx'
import { createPortfolio, type PortfolioDraft } from './portfolioApi.ts'
import { applyPricesToHoldings, sumWeights, weightsAreComplete } from './holdings.ts'
import { TARGET_WEIGHT_TOTAL, type Holding } from './types.ts'

const NEW_RUN_VALUE = 'new'

const FIELD_HINTS = {
  maxWeight: '45',
  riskFree: '4',
  strategy: 'Choose a strategy',
  targetReturn: '8',
  targetVolatility: '12',
}

function optionalNumberText(value: number): string {
  return value > 0 ? String(value) : ''
}

export default function PortfolioAnalysisPage() {
  const navigate = useNavigate()
  const { userId, isSignedIn, getToken } = useAuth()
  const { pendingDraft, draftRevision, noteSaved, portfolios, activeId } = useActivePortfolio()
  const [portfolioName, setPortfolioName] = useState('')
  const [initialCapital, setInitialCapital] = useState(0)
  const [strategy, setStrategy] = useState('')
  const [maxWeight, setMaxWeight] = useState('')
  const [riskFree, setRiskFree] = useState('')
  const [targetReturn, setTargetReturn] = useState('')
  const [targetVolatility, setTargetVolatility] = useState('')
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [historyKey, setHistoryKey] = useState(0)
  const [runSummaries, setRunSummaries] = useState<OptimizationRunSummary[]>([])
  const [selectedRunId, setSelectedRunId] = useState(NEW_RUN_VALUE)
  const [runsBusy, setRunsBusy] = useState(false)
  const [runsError, setRunsError] = useState<string | null>(null)

  const token = useCallback(async () => {
    const value = await getToken()
    if (!value) throw new Error('Sign in to manage saved runs.')
    return value
  }, [getToken])

  const parsedMaxWeight = Number(maxWeight)
  const parsedRiskFree = Number(riskFree)
  const parsedTargetReturn = Number(targetReturn)
  const parsedTargetVolatility = Number(targetVolatility)
  const missingForRun = useMemo(() => {
    const missing: string[] = []
    if (!portfolioName.trim()) missing.push('a saved portfolio (open Portfolio manager first)')
    if (!(initialCapital > 0)) missing.push('initial portfolio value from setup')
    if (!strategy) missing.push('strategy')
    if (!(maxWeight.trim() && Number.isFinite(parsedMaxWeight) && parsedMaxWeight > 0)) {
      missing.push('maximum weight')
    }
    if (!(riskFree.trim() && Number.isFinite(parsedRiskFree))) missing.push('risk-free rate')
    if (
      strategy === 'target_return' &&
      !(targetReturn.trim() && Number.isFinite(parsedTargetReturn))
    ) {
      missing.push('target return')
    }
    if (
      strategy === 'target_risk' &&
      !(
        targetVolatility.trim() &&
        Number.isFinite(parsedTargetVolatility) &&
        parsedTargetVolatility > 0
      )
    ) {
      missing.push('target volatility')
    }
    if (!startDate || !endDate) missing.push('start and end dates')
    else if (!(startDate < endDate)) missing.push('a start date before the end date')
    if (holdings.length < 2) missing.push('at least two assets from setup')
    else if (!weightsAreComplete(holdings)) missing.push('weights that total 100% from setup')
    return missing
  }, [
    portfolioName,
    initialCapital,
    strategy,
    maxWeight,
    parsedMaxWeight,
    riskFree,
    parsedRiskFree,
    targetReturn,
    parsedTargetReturn,
    targetVolatility,
    parsedTargetVolatility,
    startDate,
    endDate,
    holdings,
  ])
  const readyForAnalysis = missingForRun.length === 0
  const hasHoldings = holdings.length > 0

  function clearAnalysisSettings() {
    setStartDate('')
    setEndDate('')
    setStrategy('')
    setMaxWeight('')
    setRiskFree('')
    setTargetReturn('')
    setTargetVolatility('')
    setHistoryKey((current) => current + 1)
  }

  function applyRunParams(params: OptimizationRunParams) {
    const maxWeightPercent =
      params.max_weight == null ? '' : optionalNumberText(params.max_weight * 100)
    const riskFreePercent =
      params.risk_free_rate == null ? '' : String(params.risk_free_rate * 100)
    setStartDate(params.start_date ?? '')
    setEndDate(params.end_date ?? '')
    setStrategy(params.strategy ?? '')
    setMaxWeight(maxWeightPercent)
    setRiskFree(riskFreePercent)
    setTargetReturn(
      params.target_return == null ? '' : String(params.target_return * 100),
    )
    setTargetVolatility(
      params.target_volatility == null ? '' : String(params.target_volatility * 100),
    )
    setHistoryKey((current) => current + 1)
  }

  function handleLoadPortfolio(draft: PortfolioDraft) {
    setPortfolioName(draft.portfolioName)
    setInitialCapital(draft.initialCapital)
    setHoldings(draft.holdings)
    // New analysis starts blank; saved runs restore their own settings when selected.
    clearAnalysisSettings()
    setSelectedRunId(NEW_RUN_VALUE)
    setRunError(null)
    setRunsError(null)
  }

  useEffect(() => {
    if (draftRevision > 0 && pendingDraft) handleLoadPortfolio(pendingDraft)
  }, [draftRevision, pendingDraft])

  const refreshRuns = useCallback(async () => {
    if (!activeId || !isSignedIn) {
      setRunSummaries([])
      setSelectedRunId(NEW_RUN_VALUE)
      setRunsError(null)
      return
    }
    setRunsBusy(true)
    setRunsError(null)
    try {
      const rows = await listOptimizationRuns(activeId, await token())
      setRunSummaries(rows)
      setSelectedRunId((current) =>
        current !== NEW_RUN_VALUE && rows.some((row) => row.id === current)
          ? current
          : NEW_RUN_VALUE,
      )
    } catch (caught) {
      setRunSummaries([])
      setSelectedRunId(NEW_RUN_VALUE)
      setRunsError(
        caught instanceof ApiError
          ? `${caught.code}: ${caught.message}`
          : caught instanceof Error
            ? caught.message
            : 'Could not load saved runs.',
      )
    } finally {
      setRunsBusy(false)
    }
  }, [activeId, isSignedIn, token])

  useEffect(() => {
    void refreshRuns()
  }, [refreshRuns])

  useEffect(() => {
    if (!activeId || selectedRunId === NEW_RUN_VALUE || !isSignedIn) return
    let cancelled = false
    setRunsBusy(true)
    void (async () => {
      try {
        const detail = await readOptimizationRun(activeId, selectedRunId, await token())
        if (cancelled) return
        applyRunParams(detail.params)
        setRunsError(null)
      } catch (caught) {
        if (cancelled) return
        setRunsError(
          caught instanceof ApiError
            ? `${caught.code}: ${caught.message}`
            : caught instanceof Error
              ? caught.message
              : 'Could not load the selected run.',
        )
      } finally {
        if (!cancelled) setRunsBusy(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [activeId, selectedRunId, isSignedIn, token])

  function handleRunSelection(value: string) {
    setSelectedRunId(value)
    if (value === NEW_RUN_VALUE) {
      clearAnalysisSettings()
    }
  }

  async function handleDeleteRun(runId: string) {
    if (!activeId) return
    setRunsBusy(true)
    setRunsError(null)
    try {
      await deleteOptimizationRun(activeId, runId, await token())
      clearLastOptimizationRun(userId ?? null, activeId)
      const rows = await listOptimizationRuns(activeId, await token())
      setRunSummaries(rows)
      if (selectedRunId === runId) {
        setSelectedRunId(NEW_RUN_VALUE)
      }
    } catch (caught) {
      setRunsError(
        caught instanceof ApiError
          ? `${caught.code}: ${caught.message}`
          : caught instanceof Error
            ? caught.message
            : 'Could not delete the run.',
      )
    } finally {
      setRunsBusy(false)
    }
  }

  async function prepareDraftWithPrices(): Promise<PortfolioDraft> {
    if (!portfolioName.trim()) throw new Error('Open Portfolio setup and save a portfolio first.')
    if (!strategy) throw new Error('Choose an analysis strategy.')
    if (!(parsedMaxWeight > 0) || !Number.isFinite(parsedRiskFree)) {
      throw new Error('Enter a positive maximum weight and a risk-free rate.')
    }
    if (strategy === 'target_return' && !Number.isFinite(parsedTargetReturn)) {
      throw new Error('Enter a target annual return for this strategy.')
    }
    if (
      strategy === 'target_risk' &&
      !(Number.isFinite(parsedTargetVolatility) && parsedTargetVolatility > 0)
    ) {
      throw new Error('Enter a positive target annual volatility for this strategy.')
    }
    const prices = await ensureHoldingsPrices(
      holdings.map((holding) => holding.symbol),
      startDate,
      endDate,
    )
    const nextHoldings = applyPricesToHoldings(holdings, initialCapital, prices)
    setHoldings(nextHoldings)
    return {
      portfolioName: portfolioName.trim(),
      initialCapital,
      startDate,
      endDate,
      strategy,
      maxWeightPercent: parsedMaxWeight,
      riskFreePercent: parsedRiskFree,
      targetReturnPercent: strategy === 'target_return' ? parsedTargetReturn : null,
      targetVolatilityPercent: strategy === 'target_risk' ? parsedTargetVolatility : null,
      holdings: nextHoldings,
      referencePrices: prices,
    }
  }

  async function saveDraftIfNeeded(
    draft: PortfolioDraft,
  ): Promise<{ saveNote: string | null; portfolioId: string | null }> {
    if (!isSignedIn) {
      return {
        saveNote:
          'Signed out: results stay in this browser only. Sign in to keep the portfolio on the dashboard switcher.',
        portfolioId: activeId,
      }
    }
    if (activeId) {
      return { saveNote: null, portfolioId: activeId }
    }
    const name = draft.portfolioName.trim()
    const existing = portfolios.find((row) => row.name === name)
    if (existing) {
      return { saveNote: null, portfolioId: existing.id }
    }
    try {
      const token = await getToken()
      if (!token) {
        return {
          saveNote: 'Could not read the session token. Sign in again to save portfolios.',
          portfolioId: activeId,
        }
      }
      const saved = await createPortfolio(token, draft)
      noteSaved(saved)
      return { saveNote: null, portfolioId: saved.id }
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === 'duplicate_portfolio_name') {
        const row = portfolios.find((item) => item.name === name)
        return { saveNote: null, portfolioId: row?.id ?? activeId }
      }
      return {
        saveNote:
          caught instanceof ApiError
            ? `Saved run locally, but portfolio save failed (${caught.code}: ${caught.message}).`
            : caught instanceof Error
              ? `Saved run locally, but portfolio save failed (${caught.message}).`
              : 'Saved run locally, but portfolio save failed.',
        portfolioId: activeId,
      }
    }
  }

  async function handleRunAnalysis() {
    if (!readyForAnalysis) return
    setRunning(true)
    setRunError(null)
    try {
      const draft = await prepareDraftWithPrices()
      const tickers = draft.holdings.map((holding) => holding.symbol)
      const currentWeights = draft.holdings.map((holding) => holding.weightPercent / 100)
      const maxWeightValue = draft.maxWeightPercent / 100
      const riskFreeRate = draft.riskFreePercent / 100
      const targetReturnValue =
        draft.targetReturnPercent == null ? null : draft.targetReturnPercent / 100
      const targetVolatilityValue =
        draft.targetVolatilityPercent == null ? null : draft.targetVolatilityPercent / 100
      const result = await runOptimization({
        tickers,
        startDate: draft.startDate,
        endDate: draft.endDate,
        strategy: draft.strategy,
        maxWeight: maxWeightValue,
        riskFreeRate,
        currentWeights,
        initialCapital: draft.initialCapital,
        targetReturn: targetReturnValue,
        targetVolatility: targetVolatilityValue,
      })
      const { saveNote, portfolioId } = await saveDraftIfNeeded(draft)
      let persistNote = saveNote
      if (portfolioId && isSignedIn) {
        try {
          const token = await getToken()
          if (token) {
            await saveOptimizationRun(
              portfolioId,
              {
                tickers,
                start_date: draft.startDate,
                end_date: draft.endDate,
                strategy: draft.strategy,
                max_weight: maxWeightValue,
                risk_free_rate: riskFreeRate,
                target_return: targetReturnValue,
                target_volatility: targetVolatilityValue,
                initial_capital: draft.initialCapital,
                current_weights: currentWeights,
                reference_prices: draft.referencePrices,
              },
              result,
              token,
            )
          }
        } catch (caught) {
          const detail =
            caught instanceof ApiError
              ? `${caught.code}: ${caught.message}`
              : caught instanceof Error
                ? caught.message
                : 'unknown error'
          persistNote = persistNote
            ? `${persistNote} Run history save failed (${detail}).`
            : `Saved run locally, but run history save failed (${detail}).`
        }
      }
      saveLastOptimizationRun(
        {
          result,
          holdings: draft.holdings,
          portfolioName: draft.portfolioName,
          referencePrices: draft.referencePrices,
          initialCapital: draft.initialCapital,
          saveNote: persistNote,
          portfolioId,
        },
        userId,
        portfolioId,
      )
      navigate('/')
    } catch (caught) {
      setRunError(
        caught instanceof ApiError
          ? `${caught.code}: ${caught.message}`
          : caught instanceof Error
            ? caught.message
            : 'Optimization failed.',
      )
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">Portfolio analysis</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Choose the historical period and strategy for the selected portfolio, then run
            optimization. Holdings are edited in Portfolio manager.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            {startDate && endDate
              ? `Period ${startDate} to ${endDate}`
              : 'Pick a portfolio below to analyze'}
          </p>
        </div>
        <div className="w-full min-w-[20rem] max-w-xl shrink-0 space-y-3">
          <PortfolioSwitcher
            mode="select"
            label="Portfolio"
            className="w-full max-w-none sm:items-stretch"
          />
          {activeId && (
            <RunSwitcher
              label="Run"
              runs={runSummaries}
              selectedRunId={selectedRunId}
              busy={runsBusy || !isSignedIn}
              error={runsError}
              allowNew
              newValue={NEW_RUN_VALUE}
              newLabel="New analysis"
              emptyMessage="No saved runs yet."
              onSelect={handleRunSelection}
              onDelete={handleDeleteRun}
              onOpen={() => void refreshRuns()}
              className="w-full max-w-none sm:items-stretch"
            />
          )}
        </div>
      </div>

      {!hasHoldings && (
        <Alert>
          <AlertDescription>
            No holdings loaded yet. Use the dropdown to pick a saved portfolio, or open{' '}
            <Link to="/setup" className="underline">
              Portfolio manager
            </Link>{' '}
            to add assets.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Holdings for this run</CardTitle>
              <CardDescription>
                Read-only summary from setup. Weights should total {TARGET_WEIGHT_TOTAL}%.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {hasHoldings ? (
                <ul className="space-y-2 text-sm">
                  {holdings.map((holding) => (
                    <li
                      key={holding.symbol}
                      className="flex items-center justify-between gap-3 border-b border-border/60 py-2 last:border-0"
                    >
                      <span className="font-medium">{holding.symbol}</span>
                      <span className="text-muted-foreground">
                        {holding.weightPercent.toFixed(1)}%
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">No holdings yet.</p>
              )}
              <p className="mt-3 text-xs text-muted-foreground">
                {holdings.length} assets · Weights {sumWeights(holdings).toFixed(0)}% /{' '}
                {TARGET_WEIGHT_TOTAL}% · Capital{' '}
                {initialCapital > 0 ? `$${initialCapital.toLocaleString()}` : '—'}
              </p>
              <Button asChild variant="outline" size="sm" className="mt-4">
                <Link to="/setup">Edit holdings in manager</Link>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Historical period</CardTitle>
              <CardDescription>
                Choose the date range used for this run. Prices load when you run analysis.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <HistoryPeriodPanel
                key={historyKey}
                startDate={startDate}
                endDate={endDate}
                onStartDateChange={setStartDate}
                onEndDateChange={setEndDate}
              />
            </CardContent>
          </Card>
        </div>

        <Card className="h-fit xl:sticky xl:top-6">
          <CardHeader>
            <CardTitle>Analysis settings</CardTitle>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <Field>
                <FieldLabel>Strategy</FieldLabel>
                <Select value={strategy || undefined} onValueChange={setStrategy}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder={FIELD_HINTS.strategy} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="min_variance">Minimum variance (lowest risk)</SelectItem>
                    <SelectItem value="max_sharpe">
                      Maximum Sharpe ratio (best return for its risk)
                    </SelectItem>
                    <SelectItem value="target_return">
                      Target return (lowest risk for a return goal)
                    </SelectItem>
                    <SelectItem value="target_risk">
                      Target risk (highest return under a volatility cap)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              {strategy === 'target_return' && (
                <Field>
                  <FieldLabel htmlFor="target-return">Target annual return (%)</FieldLabel>
                  <Input
                    id="target-return"
                    value={targetReturn}
                    placeholder={FIELD_HINTS.targetReturn}
                    inputMode="decimal"
                    onChange={(event) => setTargetReturn(event.target.value)}
                  />
                </Field>
              )}
              {strategy === 'target_risk' && (
                <Field>
                  <FieldLabel htmlFor="target-volatility">
                    Target annual volatility (%)
                  </FieldLabel>
                  <Input
                    id="target-volatility"
                    value={targetVolatility}
                    placeholder={FIELD_HINTS.targetVolatility}
                    inputMode="decimal"
                    onChange={(event) => setTargetVolatility(event.target.value)}
                  />
                </Field>
              )}
              <Field>
                <FieldLabel htmlFor="max-weight">Maximum weight per asset (%)</FieldLabel>
                <Input
                  id="max-weight"
                  value={maxWeight}
                  placeholder={FIELD_HINTS.maxWeight}
                  inputMode="decimal"
                  onChange={(event) => setMaxWeight(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="risk-free">Assumed annual risk-free rate (%)</FieldLabel>
                <Input
                  id="risk-free"
                  value={riskFree}
                  placeholder={FIELD_HINTS.riskFree}
                  inputMode="decimal"
                  onChange={(event) => setRiskFree(event.target.value)}
                />
              </Field>
              <FieldDescription>
                Each run is saved under this portfolio when you are signed in. You can run the same
                holdings with different periods or strategies.
              </FieldDescription>
            </FieldGroup>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardFooter className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-medium">Ready to run analysis</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Results are historical estimates
              {startDate && endDate ? ` for ${startDate} to ${endDate}` : ''}, not guaranteed
              outcomes.
            </p>
            {!readyForAnalysis && (
              <p className="mt-2 text-sm text-amber-700">
                Still needed: {missingForRun.join(', ')}.
              </p>
            )}
            {runError && (
              <Alert variant="destructive" className="mt-3">
                <AlertDescription>{runError}</AlertDescription>
              </Alert>
            )}
          </div>
          <Button
            type="button"
            disabled={!readyForAnalysis || running}
            title={
              readyForAnalysis
                ? 'Load prices, run optimization, and save the run when signed in.'
                : `Still needed: ${missingForRun.join(', ')}.`
            }
            onClick={() => void handleRunAnalysis()}
          >
            {running ? 'Loading prices & running…' : 'Run analysis'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
