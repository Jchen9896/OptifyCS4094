import { useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ApiError } from '@/lib/apiClient'
import type { Holding } from '../portfolio/types.ts'
import { fetchPriceHistory, type PriceHistoryResponse } from './historyApi.ts'

type HistoryPeriodPanelProps = {
  holdings: Holding[]
  startDate: string
  endDate: string
  onStartDateChange: (value: string) => void
  onEndDateChange: (value: string) => void
}

type CoverageRow = {
  symbol: string
  status: 'ok' | 'error'
  summary: string
  servedFromDatabase?: boolean
}

export default function HistoryPeriodPanel({
  holdings,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
}: HistoryPeriodPanelProps) {
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
          summary: `${result.bar_count} bars · ${span}`,
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
      <FieldGroup className="grid gap-4 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="start-date">Start date</FieldLabel>
          <Input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(event) => onStartDateChange(event.target.value)}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="end-date">End date</FieldLabel>
          <Input
            id="end-date"
            type="date"
            value={endDate}
            onChange={(event) => onEndDateChange(event.target.value)}
          />
        </Field>
      </FieldGroup>

      <Button type="button" onClick={() => void loadPrices()} disabled={loading}>
        {loading ? 'Loading prices…' : 'Load prices'}
      </Button>

      {formError && (
        <Alert variant="destructive">
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <div>
        <p className="text-sm font-medium">Adjusted daily prices</p>
        <FieldDescription>
          Coverage uses stored price bars when available; otherwise the provider fills gaps.
        </FieldDescription>
      </div>

      {rows.length > 0 && (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Coverage</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.symbol}>
                  <TableCell className="font-medium">{row.symbol}</TableCell>
                  <TableCell
                    className={
                      row.status === 'ok' ? 'text-muted-foreground' : 'text-destructive'
                    }
                  >
                    {row.summary}
                  </TableCell>
                  <TableCell>
                    {row.status === 'ok' ? (
                      <Badge variant="secondary">
                        {row.servedFromDatabase ? 'Complete — database' : 'Complete — provider'}
                      </Badge>
                    ) : (
                      <Badge variant="destructive">Needs attention</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
