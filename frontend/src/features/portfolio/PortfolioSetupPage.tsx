import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
import {
  runOptimization,
  saveLastOptimizationRun,
} from '../optimization/optimizationApi.ts'
import StockSearch from '../stock-search/components/StockSearch.tsx'
import type { StockSearchResult } from '../stock-search/stockApi.ts'
import HoldingsTable from './components/HoldingsTable.tsx'
import {
  addHolding,
  removeHolding,
  resyncQuantities,
  sumWeights,
  updateHoldingWeight,
  weightsAreComplete,
} from './holdings.ts'
import { TARGET_WEIGHT_TOTAL, type Holding } from './types.ts'

function defaultEndDate(): string {
  return new Date().toISOString().slice(0, 10)
}

function defaultStartDate(): string {
  const end = new Date()
  const start = new Date(end)
  start.setFullYear(end.getFullYear() - 1)
  return start.toISOString().slice(0, 10)
}

export default function PortfolioSetupPage() {
  const navigate = useNavigate()
  const [portfolioName, setPortfolioName] = useState('Sample portfolio')
  const [initialPortfolioValue, setInitialPortfolioValue] = useState('100000')
  const [strategy, setStrategy] = useState('min_variance')
  const [maxWeight, setMaxWeight] = useState('45')
  const [riskFree, setRiskFree] = useState('4')
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [referencePrices, setReferencePrices] = useState<Record<string, number>>({})
  const [startDate, setStartDate] = useState(defaultStartDate)
  const [endDate, setEndDate] = useState(defaultEndDate)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  const disabledSymbols = useMemo(
    () => new Set(holdings.map((holding) => holding.symbol)),
    [holdings],
  )
  const parsedInitialValue = Number(initialPortfolioValue)
  const initialValue =
    Number.isFinite(parsedInitialValue) && parsedInitialValue > 0 ? parsedInitialValue : 0
  const readyForAnalysis = holdings.length >= 2 && weightsAreComplete(holdings) && initialValue > 0

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

  function handlePricesLoaded(prices: Record<string, number>) {
    setReferencePrices(prices)
    if (initialValue > 0) {
      setHoldings((current) => resyncQuantities(current, initialValue, prices))
    }
  }

  async function handleRunAnalysis() {
    if (!readyForAnalysis) {
      return
    }
    setRunning(true)
    setRunError(null)
    const maxWeightPercent = Number(maxWeight)
    const riskFreePercent = Number(riskFree)
    try {
      const result = await runOptimization({
        tickers: holdings.map((holding) => holding.symbol),
        startDate,
        endDate,
        strategy,
        maxWeight:
          Number.isFinite(maxWeightPercent) && maxWeightPercent > 0
            ? maxWeightPercent / 100
            : null,
        riskFreeRate: Number.isFinite(riskFreePercent) ? riskFreePercent / 100 : null,
        currentWeights: holdings.map((holding) => holding.weightPercent / 100),
        initialCapital: initialValue,
      })
      saveLastOptimizationRun({
        result,
        holdings,
        portfolioName,
        referencePrices,
        initialCapital: initialValue,
      })
      navigate('/')
    } catch (caught) {
      setRunError(
        caught instanceof ApiError ? `${caught.code}: ${caught.message}` : 'Optimization failed.',
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
            Illustrative sample · As of {new Date().toLocaleDateString()} · Load prices to retrieve
            market data
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button">Create new portfolio</Button>
          <Button type="button">Save portfolio</Button>
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
                    onChange={(event) => setPortfolioName(event.target.value)}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="initial-value">Initial portfolio value (USD)</FieldLabel>
                  <Input
                    id="initial-value"
                    value={initialPortfolioValue}
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
                Search by ticker or company name, then set weights that total 100%. Quantities are
                estimated from weight, initial portfolio value, and the last loaded adjusted close.
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
                Choose start and end dates, then load adjusted daily prices for each selected asset.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <HistoryPeriodPanel
                holdings={holdings}
                startDate={startDate}
                endDate={endDate}
                onStartDateChange={setStartDate}
                onEndDateChange={setEndDate}
                onPricesLoaded={handlePricesLoaded}
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
                <Select value={strategy} onValueChange={setStrategy}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="min_variance">Minimum variance (lowest risk)</SelectItem>
                    <SelectItem value="max_sharpe">Maximum Sharpe ratio (best return for its risk)</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel htmlFor="max-weight">Maximum weight per asset</FieldLabel>
                <Input
                  id="max-weight"
                  value={maxWeight}
                  onChange={(event) => setMaxWeight(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="risk-free">Assumed annual risk-free rate</FieldLabel>
                <Input
                  id="risk-free"
                  value={riskFree}
                  onChange={(event) => setRiskFree(event.target.value)}
                />
              </Field>
              <FieldDescription>
                Load prices for the selected period first. The run uses stored bars only.
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
              {TARGET_WEIGHT_TOTAL}% · Max {maxWeight}% · Risk-free rate {riskFree}%
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Results are historical estimates for {startDate} to {endDate}, not guaranteed outcomes.
            </p>
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
                ? 'Run the selected optimization on stored prices.'
                : 'Add at least two assets, set weights to 100%, and enter a positive initial value.'
            }
            onClick={() => void handleRunAnalysis()}
          >
            {running ? 'Running…' : 'Review & run analysis'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
