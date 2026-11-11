import { useEffect, useMemo, useState } from 'react'
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
  runOptimization,
  saveLastOptimizationRun,
  saveOptimizationRun,
} from '../optimization/optimizationApi.ts'
import StockSearch from '../stock-search/components/StockSearch.tsx'
import type { StockSearchResult } from '../stock-search/stockApi.ts'
import { useActivePortfolio } from './ActivePortfolioContext.tsx'
import HoldingsTable from './components/HoldingsTable.tsx'
import { createPortfolio, type PortfolioDraft } from './portfolioApi.ts'
import {
  addHolding,
  removeHolding,
  resyncQuantities,
  sumWeights,
  updateHoldingWeight,
  weightsAreComplete,
} from './holdings.ts'
import { TARGET_WEIGHT_TOTAL, type Holding } from './types.ts'

const FIELD_HINTS = {
  portfolioName: 'Growth portfolio',
  initialCapital: '100000',
  maxWeight: '45',
  riskFree: '4',
  strategy: 'Choose a strategy',
  targetReturn: '8',
  targetVolatility: '12',
}

function optionalNumberText(value: number): string {
  return value > 0 ? String(value) : ''
}

export default function PortfolioSetupPage() {
  const navigate = useNavigate()
  const { userId, isSignedIn, getToken } = useAuth()
  const { pendingDraft, draftRevision, noteSaved, portfolios, activeId } = useActivePortfolio()
  const [portfolioName, setPortfolioName] = useState('')
  const [initialPortfolioValue, setInitialPortfolioValue] = useState('')
  const [strategy, setStrategy] = useState('')
  const [maxWeight, setMaxWeight] = useState('')
  const [riskFree, setRiskFree] = useState('')
  const [targetReturn, setTargetReturn] = useState('')
  const [targetVolatility, setTargetVolatility] = useState('')
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [referencePrices, setReferencePrices] = useState<Record<string, number>>({})
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [historyKey, setHistoryKey] = useState(0)

  const disabledSymbols = useMemo(
    () => new Set(holdings.map((holding) => holding.symbol)),
    [holdings],
  )
  const parsedInitialValue = Number(initialPortfolioValue)
  const initialValue =
    Number.isFinite(parsedInitialValue) && parsedInitialValue > 0 ? parsedInitialValue : 0
  const parsedMaxWeight = Number(maxWeight)
  const parsedRiskFree = Number(riskFree)
  const parsedTargetReturn = Number(targetReturn)
  const parsedTargetVolatility = Number(targetVolatility)
  const missingForRun = useMemo(() => {
    const missing: string[] = []
    if (!portfolioName.trim()) missing.push('portfolio name')
    if (!(initialValue > 0)) missing.push('initial portfolio value')
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
    if (holdings.length < 2) missing.push('at least two assets')
    else if (!weightsAreComplete(holdings)) missing.push('weights that total 100%')
    return missing
  }, [
    portfolioName,
    initialValue,
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

  function handleAdd(stock: StockSearchResult) {
    setHoldings((current) =>
      addHolding(current, {
        symbol: stock.symbol,
        name: stock.name,
        quoteType: stock.quote_type,
      }),
    )
  }

  function handleInitialValueChange(value: string) {
    setInitialPortfolioValue(value)
    const next = Number(value)
    if (!(Number.isFinite(next) && next > 0)) {
      return
    }
    setHoldings((current) => resyncQuantities(current, next, referencePrices))
  }

  function handleLoadPortfolio(draft: PortfolioDraft) {
    const isBlank = !draft.portfolioName && !draft.strategy && draft.holdings.length === 0
    setPortfolioName(draft.portfolioName)
    setInitialPortfolioValue(optionalNumberText(draft.initialCapital))
    setStartDate(draft.startDate)
    setEndDate(draft.endDate)
    setStrategy(draft.strategy)
    setMaxWeight(optionalNumberText(draft.maxWeightPercent))
    setRiskFree(isBlank ? '' : String(draft.riskFreePercent))
    setTargetReturn(
      draft.targetReturnPercent == null ? '' : String(draft.targetReturnPercent),
    )
    setTargetVolatility(
      draft.targetVolatilityPercent == null ? '' : String(draft.targetVolatilityPercent),
    )
    setHoldings(draft.holdings)
    setReferencePrices(draft.referencePrices)
    setRunError(null)
    setHistoryKey((current) => current + 1)
  }

  useEffect(() => {
    if (draftRevision > 0 && pendingDraft) handleLoadPortfolio(pendingDraft)
  }, [draftRevision, pendingDraft])

  async function prepareDraftWithPrices(): Promise<PortfolioDraft> {
    if (!portfolioName.trim()) throw new Error('Enter a portfolio name.')
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
    const nextHoldings = resyncQuantities(holdings, initialValue, prices)
    setReferencePrices(prices)
    setHoldings(nextHoldings)
    return {
      portfolioName: portfolioName.trim(),
      initialCapital: initialValue,
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
    if (!readyForAnalysis) {
      return
    }
    setRunning(true)
    setRunError(null)
    try {
      const draft = await prepareDraftWithPrices()
      const tickers = draft.holdings.map((holding) => holding.symbol)
      const currentWeights = draft.holdings.map((holding) => holding.weightPercent / 100)
      const maxWeightValue = draft.maxWeightPercent / 100
      const riskFreeRate = draft.riskFreePercent / 100
      const targetReturn =
        draft.targetReturnPercent == null ? null : draft.targetReturnPercent / 100
      const targetVolatility =
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
        targetReturn,
        targetVolatility,
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
                target_return: targetReturn,
                target_volatility: targetVolatility,
                initial_capital: draft.initialCapital,
                current_weights: currentWeights,
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
          <h1 className="font-heading text-2xl font-semibold">Portfolio setup</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Choose stocks and ETFs, set your current allocation, and define the assumptions for a
            historical analysis.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Illustrative sample · As of {new Date().toLocaleDateString()} · Running analysis loads
            prices and saves the portfolio when you are signed in
          </p>
          {!isSignedIn && (
            <p className="mt-2 text-sm text-muted-foreground">
              <Link to="/login" className="underline">
                Sign in
              </Link>{' '}
              to keep portfolios on the dashboard switcher after a run.
            </p>
          )}
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>1. Name your portfolio</CardTitle>
            </CardHeader>
            <CardContent>
              <FieldGroup className="grid gap-4 sm:grid-cols-2">
                <Field>
                  <FieldLabel htmlFor="portfolio-name">Portfolio name</FieldLabel>
                  <Input
                    id="portfolio-name"
                    value={portfolioName}
                    placeholder={FIELD_HINTS.portfolioName}
                    onChange={(event) => setPortfolioName(event.target.value)}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="initial-value">Initial portfolio value (USD)</FieldLabel>
                  <Input
                    id="initial-value"
                    value={initialPortfolioValue}
                    placeholder={FIELD_HINTS.initialCapital}
                    inputMode="decimal"
                    onChange={(event) => handleInitialValueChange(event.target.value)}
                  />
                  <FieldDescription>
                    Scales equity charts and estimated share counts. No brokerage funds are
                    connected.
                  </FieldDescription>
                </Field>
              </FieldGroup>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>2. Select assets and set weights</CardTitle>
              <CardDescription>
                Search by ticker or company name, then set weights that total 100%. Share quantities
                are estimated from prices when you run analysis.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <StockSearch onAdd={handleAdd} disabledSymbols={disabledSymbols} />
              <HoldingsTable
                holdings={holdings}
                prices={referencePrices}
                onWeightChange={(symbol, weightPercent) =>
                  setHoldings((current) =>
                    updateHoldingWeight(
                      current,
                      symbol,
                      weightPercent,
                      initialValue,
                      referencePrices,
                    ),
                  )
                }
                onRemove={(symbol) => setHoldings((current) => removeHolding(current, symbol))}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>4. Set the historical period</CardTitle>
              <CardDescription>
                Choose the date range used for analysis. Prices for that range load automatically
                when you run analysis.
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
            <CardTitle>3. Choose your analysis settings</CardTitle>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <Field>
                <FieldLabel>Strategy</FieldLabel>
                <Select
                  value={strategy || undefined}
                  onValueChange={setStrategy}
                >
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
                Running analysis loads prices, optimizes, and saves the portfolio when you are signed
                in.
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
              {holdings.length} assets · Weights {sumWeights(holdings).toFixed(0)}% /{' '}
              {TARGET_WEIGHT_TOTAL}% · Max {maxWeight || '—'}% · Risk-free rate {riskFree || '—'}%
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Results are historical estimates
              {startDate && endDate ? ` for ${startDate} to ${endDate}` : ''}
              , not guaranteed outcomes.
              {isSignedIn
                ? ' A new portfolio name is saved to your account on this run.'
                : ' Sign in to save the portfolio to your account.'}
            </p>
            {!readyForAnalysis && (
              <p className="mt-2 text-sm text-amber-700">
                Still needed: {missingForRun.join(', ')}. Gray placeholder text is only a hint — type
                real values into each field.
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
                ? 'Load prices, run optimization, and save the portfolio when signed in.'
                : `Still needed: ${missingForRun.join(', ')}.`
            }
            onClick={() => void handleRunAnalysis()}
          >
            {running ? 'Loading prices & running…' : 'Review & run analysis'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
