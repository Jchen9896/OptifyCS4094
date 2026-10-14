import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import HistoryPeriodPanel from '../history-period/HistoryPeriodPanel.tsx'
import StockSearch from '../stock-search/components/StockSearch.tsx'
import type { StockSearchResult } from '../stock-search/stockApi.ts'
import HoldingsTable from './components/HoldingsTable.tsx'
import {
  addHolding,
  removeHolding,
  sumWeights,
  updateHoldingWeight,
  weightsAreComplete,
} from './holdings.ts'
import { TARGET_WEIGHT_TOTAL, type Holding } from './types.ts'

export default function PortfolioSetupPage() {
  const [portfolioName, setPortfolioName] = useState('Sample portfolio')
  const [notionalValue, setNotionalValue] = useState('248500')
  const [strategy, setStrategy] = useState('mvo')
  const [objective, setObjective] = useState('sharpe')
  const [maxWeight, setMaxWeight] = useState('45')
  const [keepAsset, setKeepAsset] = useState(true)
  const [mustKeep, setMustKeep] = useState('AGG')
  const [minWeight, setMinWeight] = useState('5')
  const [riskFree, setRiskFree] = useState('4')
  const [holdings, setHoldings] = useState<Holding[]>([])

  const disabledSymbols = useMemo(
    () => new Set(holdings.map((holding) => holding.symbol)),
    [holdings],
  )
  const readyForAnalysis = holdings.length > 0 && weightsAreComplete(holdings)

  function handleAdd(stock: StockSearchResult) {
    setHoldings((current) =>
      addHolding(current, {
        symbol: stock.symbol,
        name: stock.name,
        quoteType: stock.quote_type,
      }),
    )
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
          <Button type="button" variant="outline">
            Create new portfolio
          </Button>
          <Button type="button" variant="outline">
            Save portfolio
          </Button>
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
                  <FieldLabel htmlFor="notional">Notional portfolio value (USD)</FieldLabel>
                  <Input
                    id="notional"
                    value={notionalValue}
                    onChange={(event) => setNotionalValue(event.target.value)}
                  />
                  <FieldDescription>
                    For context only. No brokerage funds are connected.
                  </FieldDescription>
                </Field>
              </FieldGroup>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>2. Select assets and set weights</CardTitle>
              <CardDescription>
                Search by ticker or company name, then set weights that total 100%.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <StockSearch onAdd={handleAdd} disabledSymbols={disabledSymbols} />
              <HoldingsTable
                holdings={holdings}
                onWeightChange={(symbol, weightPercent) =>
                  setHoldings((current) => updateHoldingWeight(current, symbol, weightPercent))
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
              <HistoryPeriodPanel holdings={holdings} />
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
                    <SelectItem value="mvo">Mean-Variance Optimization</SelectItem>
                    <SelectItem value="minvar">Minimum variance</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel>Objective</FieldLabel>
                <Select value={objective} onValueChange={setObjective}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sharpe">Maximize Sharpe ratio</SelectItem>
                    <SelectItem value="variance">Minimize variance</SelectItem>
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
              <Field orientation="horizontal">
                <Checkbox
                  id="keep-asset"
                  checked={keepAsset}
                  onCheckedChange={(checked) => setKeepAsset(checked === true)}
                />
                <FieldLabel htmlFor="keep-asset" className="font-normal">
                  Keep an asset in the optimized portfolio
                </FieldLabel>
              </Field>
              {keepAsset && (
                <>
                  <Field>
                    <FieldLabel>Must-keep asset</FieldLabel>
                    <Select value={mustKeep} onValueChange={setMustKeep}>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="AGG">AGG</SelectItem>
                        {holdings.map((holding) => (
                          <SelectItem key={holding.symbol} value={holding.symbol}>
                            {holding.symbol}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="min-weight">Minimum weight</FieldLabel>
                    <Input
                      id="min-weight"
                      value={minWeight}
                      onChange={(event) => setMinWeight(event.target.value)}
                    />
                  </Field>
                </>
              )}
              <Field>
                <FieldLabel htmlFor="risk-free">Assumed annual risk-free rate</FieldLabel>
                <Input
                  id="risk-free"
                  value={riskFree}
                  onChange={(event) => setRiskFree(event.target.value)}
                />
              </Field>
              <FieldDescription>
                Settings are captured in the UI. Optimization runs when the backend endpoint is
                connected.
              </FieldDescription>
            </FieldGroup>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardFooter className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-medium">Ready to review the sample</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {holdings.length} assets · Weights {sumWeights(holdings).toFixed(0)}% /{' '}
              {TARGET_WEIGHT_TOTAL}% · Max {maxWeight}% · Risk-free rate {riskFree}%
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Optify is a decision-support tool. Inputs and results on this page may be illustrative.
            </p>
          </div>
          <Button
            type="button"
            disabled
            title={
              readyForAnalysis
                ? 'Optimization API is not available yet.'
                : 'Add assets and set weights to 100% first.'
            }
          >
            Review & run analysis
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
