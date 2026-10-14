import { useMemo, useState } from 'react'
import HistoryPeriodPanel from '../history-period/HistoryPeriodPanel.tsx'
import StockSearch from '../stock-search/components/StockSearch.tsx'
import type { StockSearchResult } from '../stock-search/stockApi.ts'
import HoldingsTable from './components/HoldingsTable.tsx'
import { addHolding, removeHolding, updateHoldingWeight } from './holdings.ts'
import type { Holding } from './types.ts'

export default function PortfolioSetupPage() {
  const [holdings, setHoldings] = useState<Holding[]>([])
  const disabledSymbols = useMemo(
    () => new Set(holdings.map((holding) => holding.symbol)),
    [holdings],
  )

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
          Choose stocks and ETFs for analysis. Holdings stay in this browser session for now.
        </p>
      </div>

      <div className="rounded-xl border border-line bg-panel p-5">
        <h2 className="text-lg font-medium text-paper">Select assets and set weights</h2>
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
        <h2 className="text-lg font-medium text-paper">Set the historical period</h2>
        <p className="mt-1 text-sm text-muted">
          Choose start and end dates, then load adjusted daily prices for each selected asset.
        </p>
        <div className="mt-4">
          <HistoryPeriodPanel holdings={holdings} />
        </div>
      </div>
    </section>
  )
}
