import { useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/apiClient'
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
      <Field>
        <FieldLabel htmlFor="stock-search">Search by ticker or company name</FieldLabel>
        <div className="flex gap-2">
          <Input
            id="stock-search"
            className="min-w-0 flex-1"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                void runSearch()
              }
            }}
            placeholder="NVDA or NVIDIA"
          />
          <Button type="button" onClick={() => void runSearch()} disabled={loading}>
            {loading ? 'Searching…' : 'Search'}
          </Button>
        </div>
      </Field>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {results.length > 0 && (
        <ul className="divide-y divide-border rounded-lg border border-border bg-card">
          {results.map((stock) => {
            const alreadyAdded = disabledSymbols?.has(stock.symbol) ?? false
            return (
              <li key={stock.symbol} className="flex items-center justify-between gap-3 px-3 py-2.5">
                <div>
                  <p className="text-sm font-medium">
                    {stock.symbol}
                    <span className="ml-2 font-normal text-muted-foreground">{stock.name}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {[stock.exchange, stock.quote_type].filter(Boolean).join(' · ') || '—'}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={alreadyAdded}
                  onClick={() => onAdd(stock)}
                >
                  {alreadyAdded ? 'Added' : '+ Add'}
                </Button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
