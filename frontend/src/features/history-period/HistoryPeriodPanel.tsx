import { useState } from 'react'
import { ApiError } from '../../lib/apiClient.ts'
import type { Holding } from '../portfolio/types.ts'
import { fetchPriceHistory, type PriceHistoryResponse } from './historyApi.ts'

type HistoryPeriodPanelProps = {
  holdings: Holding[]
}

type CoverageRow = {
  symbol: string
  status: 'ok' | 'error'
  summary: string
  servedFromDatabase?: boolean
}

function defaultEndDate(): string {
  return new Date().toISOString().slice(0, 10)
}

function defaultStartDate(): string {
  const end = new Date()
  const start = new Date(end)
  start.setFullYear(end.getFullYear() - 1)
  return start.toISOString().slice(0, 10)
}

export default function HistoryPeriodPanel({ holdings }: HistoryPeriodPanelProps) {
  const [startDate, setStartDate] = useState(defaultStartDate)
  const [endDate, setEndDate] = useState(defaultEndDate)
  const [loading, setLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [rows, setRows] = useState<CoverageRow[]>([])

  async function loadPrices() {
    if (holdings.length === 0) {
      setFormError('Add at least one asset before loading prices.')
      setRows([])
      return
    }

    setLoading(true)
    setFormError(null)
    const nextRows: CoverageRow[] = []

    for (const holding of holdings) {
      try {
        const result: PriceHistoryResponse = await fetchPriceHistory({
          symbol: holding.symbol,
          startDate,
          endDate,
        })
        const span =
          result.first_date && result.last_date
            ? `${result.first_date} → ${result.last_date}`
            : 'No dates returned'
        nextRows.push({
          symbol: holding.symbol,
          status: 'ok',
          summary: `${result.bar_count} bars · ${span} · ${result.source}`,
          servedFromDatabase: result.served_from_database,
        })
      } catch (caught) {
        nextRows.push({
          symbol: holding.symbol,
          status: 'error',
          summary: caught instanceof ApiError ? `${caught.code}: ${caught.message}` : 'Load failed.',
        })
      }
    }

    setRows(nextRows)
    setLoading(false)
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm text-muted">
          Start date
          <input
            type="date"
            className="mt-1 w-full rounded-lg border border-line bg-ink px-3 py-2 text-paper"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
          />
        </label>
        <label className="block text-sm text-muted">
          End date
          <input
            type="date"
            className="mt-1 w-full rounded-lg border border-line bg-ink px-3 py-2 text-paper"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
          />
        </label>
      </div>

      <button
        type="button"
        className="rounded-lg bg-sky px-4 py-2 text-sm font-medium text-ink disabled:opacity-50"
        onClick={() => void loadPrices()}
        disabled={loading}
      >
        {loading ? 'Loading prices…' : 'Load prices'}
      </button>

      {formError && <p className="text-sm text-danger">{formError}</p>}

      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-line">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-line bg-ink text-muted">
              <tr>
                <th className="px-3 py-2 font-medium">Symbol</th>
                <th className="px-3 py-2 font-medium">Coverage</th>
                <th className="px-3 py-2 font-medium">Source</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.symbol} className="border-b border-line last:border-0">
                  <td className="px-3 py-2 font-medium text-paper">{row.symbol}</td>
                  <td className={`px-3 py-2 ${row.status === 'ok' ? 'text-muted' : 'text-danger'}`}>
                    {row.summary}
                  </td>
                  <td className="px-3 py-2 text-muted">
                    {row.status === 'ok'
                      ? row.servedFromDatabase
                        ? 'Database'
                        : 'Provider'
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
