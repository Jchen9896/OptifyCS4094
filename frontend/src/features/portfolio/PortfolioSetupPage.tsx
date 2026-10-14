import { useMemo, useState } from 'react'
import HistoryPeriodPanel from '../history-period/HistoryPeriodPanel.tsx'
import StockSearch from '../stock-search/components/StockSearch.tsx'
import type { StockSearchResult } from '../stock-search/stockApi.ts'
import HoldingsTable from './components/HoldingsTable.tsx'
import { addHolding, removeHolding, sumWeights, updateHoldingWeight, weightsAreComplete } from './holdings.ts'
import { TARGET_WEIGHT_TOTAL, type Holding } from './types.ts'

export default function PortfolioSetupPage() {
  const [portfolioName, setPortfolioName] = useState('Sample portfolio')
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
    <section className="mx-auto max-w-4xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-paper">Portfolio setup</h1>
        <p className="mt-2 text-muted">
          Choose stocks and ETFs, set your current allocation, and define the historical period for
          analysis. Holdings stay in this browser session until portfolio save lands.
        </p>
      </div>

      <div className="rounded-xl border border-line bg-panel p-5">
        <h2 className="text-lg font-medium text-paper">1. Name your portfolio</h2>
        <label className="mt-4 block text-sm text-muted">
          Portfolio name
          <input
            className="mt-1 w-full rounded-lg border border-line bg-ink px-3 py-2 text-paper"
            value={portfolioName}
            onChange={(event) => setPortfolioName(event.target.value)}
          />
        </label>
      </div>

      <div className="rounded-xl border border-line bg-panel p-5">
        <h2 className="text-lg font-medium text-paper">2. Select assets and set weights</h2>
        <p className="mt-1 text-sm text-muted">Search, add tickers, then set weights that total 100%.</p>
        <div className="mt-4">
          <StockSearch onAdd={handleAdd} disabledSymbols={disabledSymbols} />
        </div>
        <div className="mt-6">
          <HoldingsTable
            holdings={holdings}
            onWeightChange={(symbol, weightPercent) =>
              setHoldings((current) => updateHoldingWeight(current, symbol, weightPercent))
            }
            onRemove={(symbol) => setHoldings((current) => removeHolding(current, symbol))}
          />
        </div>
      </div>

      <div className="rounded-xl border border-line bg-panel p-5">
        <h2 className="text-lg font-medium text-paper">3. Analysis settings</h2>
        <p className="mt-2 text-sm text-muted">
          Strategy, constraints, and risk-free rate controls will connect when the optimization API
          is exposed. Defaults from Decision 005 remain on the backend for now.
        </p>
      </div>

      <div className="rounded-xl border border-line bg-panel p-5">
        <h2 className="text-lg font-medium text-paper">4. Set the historical period</h2>
        <p className="mt-1 text-sm text-muted">
          Choose start and end dates, then load adjusted daily prices for each selected asset.
        </p>
        <div className="mt-4">
          <HistoryPeriodPanel holdings={holdings} />
        </div>
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-medium text-paper">Ready to review</p>
          <p className="mt-1 text-sm text-muted">
            {holdings.length} asset{holdings.length === 1 ? '' : 's'} · Weights{' '}
            {sumWeights(holdings).toFixed(1)}% / {TARGET_WEIGHT_TOTAL}% · “{portfolioName || 'Untitled'}”
          </p>
          <p className="mt-1 text-xs text-muted">
            Review and run analysis stays disabled until the optimization HTTP API is available.
          </p>
        </div>
        <button
          type="button"
          className="rounded-lg bg-mint px-4 py-2 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:opacity-40"
          disabled
          title={
            readyForAnalysis
              ? 'Optimization API is not available yet.'
              : 'Add assets and set weights to 100% first.'
          }
        >
          Review & run analysis
        </button>
      </div>
    </section>
  )
}
