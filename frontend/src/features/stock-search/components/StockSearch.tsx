import { useState } from 'react'
import { ApiError } from '../../../lib/apiClient.ts'
import { searchStocks, type StockSearchResult } from '../stockApi.ts'

type StockSearchProps = {
  onAdd: (stock: StockSearchResult) => void
  disabledSymbols?: ReadonlySet<string>
}

export default function StockSearch({ onAdd, disabledSymbols }: StockSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StockSearchResult[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function runSearch() {
    const text = query.trim()
    if (!text) {
      setError('Enter a ticker or company name to search.')
      setResults([])
      return
    }

    setLoading(true)
    setError(null)
    try {
      const response = await searchStocks(text)
      setResults(response.results)
      if (response.results.length === 0) {
        setError('No stocks matched that search.')
      }
    } catch (caught) {
      setResults([])
      setError(caught instanceof ApiError ? caught.message : 'Stock search failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <label className="block text-sm text-muted">
        Search by ticker or company name
        <div className="mt-1 flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-lg border border-line bg-ink px-3 py-2 text-paper outline-none focus:border-sky"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                void runSearch()
              }
            }}
            placeholder="AAPL or Apple"
          />
          <button
            type="button"
            className="rounded-lg bg-mint px-4 py-2 text-sm font-medium text-ink disabled:opacity-50"
            onClick={() => void runSearch()}
            disabled={loading}
          >
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>
      </label>

      {error && <p className="text-sm text-danger">{error}</p>}

      {results.length > 0 && (
        <ul className="divide-y divide-line rounded-lg border border-line">
          {results.map((stock) => {
            const alreadyAdded = disabledSymbols?.has(stock.symbol) ?? false
            return (
              <li key={stock.symbol} className="flex items-center justify-between gap-3 px-3 py-2">
                <div>
                  <p className="font-medium text-paper">
                    {stock.symbol}
                    <span className="ml-2 font-normal text-muted">{stock.name}</span>
                  </p>
                  <p className="text-xs text-muted">
                    {[stock.exchange, stock.quote_type].filter(Boolean).join(' · ') || '—'}
                  </p>
                </div>
                <button
                  type="button"
                  className="rounded-md border border-line px-3 py-1 text-sm text-mint disabled:text-muted"
                  disabled={alreadyAdded}
                  onClick={() => onAdd(stock)}
                >
                  {alreadyAdded ? 'Added' : '+ Add'}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
