import { useEffect, useMemo, useRef, useState } from 'react'
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
import { ensureHoldingsPrices } from '../history-period/historyApi.ts'
import StockSearch from '../stock-search/components/StockSearch.tsx'
import type { StockSearchResult } from '../stock-search/stockApi.ts'
import { useActivePortfolio } from './ActivePortfolioContext.tsx'
import {
  BROKERAGE_OPTIONS,
  parseBrokeragePositionsCsv,
  type BrokerageId,
} from './brokerageImport.ts'
import HoldingsTable from './components/HoldingsTable.tsx'
import PortfolioSwitcher from './components/PortfolioSwitcher.tsx'
import { createPortfolio, type PortfolioDraft } from './portfolioApi.ts'
import {
  addHolding,
  applyPricesToHoldings,
  removeHolding,
  sumWeights,
  updateHoldingWeight,
  weightsAreComplete,
} from './holdings.ts'
import { TARGET_WEIGHT_TOTAL, type Holding } from './types.ts'

const FIELD_HINTS = {
  portfolioName: 'Growth portfolio',
  initialCapital: '100000',
}

function optionalNumberText(value: number): string {
  return value > 0 ? String(value) : ''
}

function isoDateUtc(date: Date): string {
  return date.toISOString().slice(0, 10)
}

function defaultHistoryRange(): { startDate: string; endDate: string } {
  const end = new Date()
  end.setUTCDate(end.getUTCDate() - 1)
  const start = new Date(end)
  start.setUTCFullYear(start.getUTCFullYear() - 1)
  return { startDate: isoDateUtc(start), endDate: isoDateUtc(end) }
}

export default function PortfolioSetupPage() {
  const navigate = useNavigate()
  const { isSignedIn, getToken } = useAuth()
  const { pendingDraft, draftRevision, noteSaved, portfolios, activeId } = useActivePortfolio()
  const [portfolioName, setPortfolioName] = useState('')
  const [initialPortfolioValue, setInitialPortfolioValue] = useState('')
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [referencePrices, setReferencePrices] = useState<Record<string, number>>({})
  const [analysisDefaults, setAnalysisDefaults] = useState({
    startDate: '',
    endDate: '',
    strategy: 'min_variance',
    maxWeightPercent: 100,
    riskFreePercent: 4,
    targetReturnPercent: null as number | null,
    targetVolatilityPercent: null as number | null,
  })
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveNote, setSaveNote] = useState<string | null>(null)
  const [importError, setImportError] = useState<string | null>(null)
  const [importNotes, setImportNotes] = useState<string[]>([])
  const [brokerage, setBrokerage] = useState<BrokerageId>('schwab')
  const csvInputRef = useRef<HTMLInputElement>(null)
  const selectedBrokerage = BROKERAGE_OPTIONS.find((option) => option.id === brokerage)
  const canImport = selectedBrokerage?.available === true

  const disabledSymbols = useMemo(
    () => new Set(holdings.map((holding) => holding.symbol)),
    [holdings],
  )
  const parsedInitialValue = Number(initialPortfolioValue)
  const initialValue =
    Number.isFinite(parsedInitialValue) && parsedInitialValue > 0 ? parsedInitialValue : 0
  const missingForSave = useMemo(() => {
    const missing: string[] = []
    if (!portfolioName.trim()) missing.push('portfolio name')
    if (!(initialValue > 0)) missing.push('initial portfolio value')
    if (holdings.length < 2) missing.push('at least two assets')
    else if (!weightsAreComplete(holdings)) missing.push('weights that total 100%')
    return missing
  }, [portfolioName, initialValue, holdings])
  const readyToSave = missingForSave.length === 0

  function handleAdd(stock: StockSearchResult) {
    setHoldings((current) =>
      addHolding(current, {
        symbol: stock.symbol,
        name: stock.name,
        quoteType: stock.quote_type,
      }),
    )
  }

  async function handleBrokerageCsv(file: File) {
    setImportError(null)
    setImportNotes([])
    try {
      if (!canImport) {
        throw new Error('Choose an available brokerage before importing.')
      }
      const text = await file.text()
      const imported = parseBrokeragePositionsCsv(brokerage, text)
      if (imported.portfolioName) setPortfolioName(imported.portfolioName)
      if (imported.initialCapital > 0) {
        setInitialPortfolioValue(String(imported.initialCapital))
      }
      setHoldings(imported.holdings)
      setReferencePrices({})
      setImportNotes(imported.notes)
    } catch (caught) {
      setImportError(
        caught instanceof Error ? caught.message : 'Could not import the brokerage CSV file.',
      )
    } finally {
      if (csvInputRef.current) csvInputRef.current.value = ''
    }
  }

  function handleInitialValueChange(value: string) {
    setInitialPortfolioValue(value)
    const next = Number(value)
    if (!(Number.isFinite(next) && next > 0)) return
    setHoldings((current) => applyPricesToHoldings(current, next, referencePrices))
  }

  function handleLoadPortfolio(draft: PortfolioDraft) {
    setPortfolioName(draft.portfolioName)
    setInitialPortfolioValue(optionalNumberText(draft.initialCapital))
    setHoldings(draft.holdings)
    setReferencePrices(draft.referencePrices)
    setAnalysisDefaults({
      startDate: draft.startDate,
      endDate: draft.endDate,
      strategy: draft.strategy || 'min_variance',
      maxWeightPercent: draft.maxWeightPercent > 0 ? draft.maxWeightPercent : 100,
      riskFreePercent: Number.isFinite(draft.riskFreePercent) ? draft.riskFreePercent : 4,
      targetReturnPercent: draft.targetReturnPercent,
      targetVolatilityPercent: draft.targetVolatilityPercent,
    })
    setSaveError(null)
    setSaveNote(null)
    setImportError(null)
    setImportNotes([])
  }

  useEffect(() => {
    if (draftRevision > 0 && pendingDraft) handleLoadPortfolio(pendingDraft)
  }, [draftRevision, pendingDraft])

  async function handleSavePortfolio() {
    if (!readyToSave) return
    setSaving(true)
    setSaveError(null)
    setSaveNote(null)
    try {
      const range =
        analysisDefaults.startDate &&
        analysisDefaults.endDate &&
        analysisDefaults.startDate < analysisDefaults.endDate
          ? {
              startDate: analysisDefaults.startDate,
              endDate: analysisDefaults.endDate,
            }
          : defaultHistoryRange()
      const prices = await ensureHoldingsPrices(
        holdings.map((holding) => holding.symbol),
        range.startDate,
        range.endDate,
      )
      const nextHoldings = applyPricesToHoldings(holdings, initialValue, prices)
      setReferencePrices(prices)
      setHoldings(nextHoldings)
      const draft: PortfolioDraft = {
        portfolioName: portfolioName.trim(),
        initialCapital: initialValue,
        startDate: range.startDate,
        endDate: range.endDate,
        strategy: analysisDefaults.strategy || 'min_variance',
        maxWeightPercent: analysisDefaults.maxWeightPercent,
        riskFreePercent: analysisDefaults.riskFreePercent,
        targetReturnPercent: analysisDefaults.targetReturnPercent,
        targetVolatilityPercent: analysisDefaults.targetVolatilityPercent,
        holdings: nextHoldings,
        referencePrices: prices,
      }

      if (!isSignedIn) {
        setSaveNote(
          'Signed out: holdings stay in this browser only. Sign in to save the portfolio, then open Portfolio analysis.',
        )
        return
      }

      const existing = portfolios.find((row) => row.name === draft.portfolioName)
      if (existing || activeId) {
        setSaveNote(
              'This portfolio is already on your account. Holdings updates need a fresh name for now — continue in Portfolio analysis, or use New portfolio in the dropdown.',
        )
        return
      }

      const token = await getToken()
      if (!token) {
        throw new Error('Could not read the session token. Sign in again to save portfolios.')
      }
      const saved = await createPortfolio(token, draft)
      noteSaved(saved)
      setSaveNote('Portfolio saved. Continue in Portfolio analysis to run a strategy.')
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === 'duplicate_portfolio_name') {
        setSaveNote('A portfolio with this name already exists. Open it from the dashboard switcher.')
        return
      }
      setSaveError(
        caught instanceof ApiError
          ? `${caught.code}: ${caught.message}`
          : caught instanceof Error
            ? caught.message
            : 'Could not save portfolio.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">Portfolio manager</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Switch portfolios, create new ones, and edit holdings and weights. Strategy and date range
            live on Portfolio analysis.
          </p>
          {!isSignedIn && (
            <p className="mt-2 text-sm text-muted-foreground">
              <Link to="/login" className="underline">
                Sign in
              </Link>{' '}
              to save portfolios to your account.
            </p>
          )}
        </div>
        <div className="w-full min-w-[20rem] max-w-xl shrink-0 space-y-3">
          <PortfolioSwitcher
            mode="manage"
            label="Portfolio"
            className="w-full max-w-none sm:items-stretch"
          />
          <div className="min-w-0 space-y-1.5">
            <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Import from brokerage (optional)
            </p>
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <Select
                value={brokerage}
                onValueChange={(value) => setBrokerage(value as BrokerageId)}
              >
                <SelectTrigger className="h-9 min-w-0 flex-1">
                  <SelectValue placeholder="Choose a brokerage" />
                </SelectTrigger>
                <SelectContent>
                  {BROKERAGE_OPTIONS.map((option) => (
                    <SelectItem
                      key={option.id}
                      value={option.id}
                      disabled={!option.available}
                    >
                      {option.available ? option.label : `${option.label} (coming soon)`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <input
                ref={csvInputRef}
                type="file"
                accept=".csv,text/csv"
                className="sr-only"
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) void handleBrokerageCsv(file)
                }}
              />
              <Button
                type="button"
                variant="outline"
                className="h-9 shrink-0"
                disabled={!canImport}
                onClick={() => csvInputRef.current?.click()}
              >
                Import CSV
              </Button>
            </div>
            {importError && (
              <Alert variant="destructive">
                <AlertDescription>{importError}</AlertDescription>
              </Alert>
            )}
            {importNotes.length > 0 && (
              <Alert>
                <AlertDescription>
                  <ul className="list-disc space-y-1 pl-4">
                    {importNotes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>1. Name your portfolio</CardTitle>
          <CardDescription>Set the portfolio name and starting value.</CardDescription>
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
                Scales equity charts and estimated share counts.
              </FieldDescription>
            </Field>
          </FieldGroup>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>2. Select assets and set weights</CardTitle>
          <CardDescription>
            Search by ticker or company name, then set weights that total 100%. Quantity is estimated
            from prices, or taken from a brokerage import.
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
        <CardFooter className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-medium">Save portfolio holdings</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {holdings.length} assets · Weights {sumWeights(holdings).toFixed(0)}% /{' '}
              {TARGET_WEIGHT_TOTAL}%
            </p>
            {!readyToSave && (
              <p className="mt-2 text-sm text-amber-700">
                Still needed: {missingForSave.join(', ')}.
              </p>
            )}
            {saveError && (
              <Alert variant="destructive" className="mt-3">
                <AlertDescription>{saveError}</AlertDescription>
              </Alert>
            )}
            {saveNote && (
              <Alert className="mt-3">
                <AlertDescription>{saveNote}</AlertDescription>
              </Alert>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate('/analyze')}
            >
              Go to analysis
            </Button>
            <Button
              type="button"
              disabled={!readyToSave || saving}
              title={
                readyToSave
                  ? 'Load prices and save the portfolio when signed in.'
                  : `Still needed: ${missingForSave.join(', ')}.`
              }
              onClick={() => void handleSavePortfolio()}
            >
              {saving ? 'Saving…' : 'Save portfolio'}
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
