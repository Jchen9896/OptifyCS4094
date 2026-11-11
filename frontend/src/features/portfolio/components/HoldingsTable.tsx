import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { sumWeights } from '../holdings.ts'
import { TARGET_WEIGHT_TOTAL, type Holding } from '../types.ts'

type HoldingsTableProps = {
  holdings: Holding[]
  prices: Record<string, number>
  onWeightChange: (symbol: string, weightPercent: number) => void
  onRemove: (symbol: string) => void
}

function formatQuantity(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return '—'
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 })
}

function displayWeight(weightPercent: number, draft: string | undefined): string {
  if (draft !== undefined) return draft
  if (weightPercent === 0) return ''
  return String(weightPercent)
}

export default function HoldingsTable({
  holdings,
  prices,
  onWeightChange,
  onRemove,
}: HoldingsTableProps) {
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const total = sumWeights(holdings)
  const totalOk = Math.abs(total - TARGET_WEIGHT_TOTAL) < 0.01

  useEffect(() => {
    const symbols = new Set(holdings.map((holding) => holding.symbol))
    setDrafts((current) => {
      const next: Record<string, string> = {}
      for (const [symbol, value] of Object.entries(current)) {
        if (symbols.has(symbol)) next[symbol] = value
      }
      return next
    })
  }, [holdings])

  if (holdings.length === 0) {
    return <p className="text-sm text-muted-foreground">No assets yet. Search and add a ticker above.</p>
  }

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Symbol</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Weight (%)</TableHead>
              <TableHead>Quantity</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {holdings.map((holding) => {
              const hasPrice = prices[holding.symbol] > 0
              return (
                <TableRow key={holding.symbol}>
                  <TableCell className="font-medium">{holding.symbol}</TableCell>
                  <TableCell className="text-muted-foreground">{holding.name}</TableCell>
                  <TableCell className="text-muted-foreground">{holding.quoteType ?? '—'}</TableCell>
                  <TableCell>
                    <Input
                      type="text"
                      inputMode="decimal"
                      className="w-24"
                      placeholder="0"
                      value={displayWeight(holding.weightPercent, drafts[holding.symbol])}
                      onChange={(event) => {
                        const raw = event.target.value
                        if (raw !== '' && !/^\d*\.?\d*$/.test(raw)) return
                        setDrafts((current) => ({ ...current, [holding.symbol]: raw }))
                        if (raw === '' || raw === '.') {
                          onWeightChange(holding.symbol, 0)
                          return
                        }
                        const next = Number(raw)
                        if (Number.isFinite(next)) onWeightChange(holding.symbol, next)
                      }}
                      onBlur={() => {
                        setDrafts((current) => {
                          const next = { ...current }
                          delete next[holding.symbol]
                          return next
                        })
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <span className="text-sm tabular-nums text-muted-foreground">
                      {hasPrice || holding.quantity > 0
                        ? formatQuantity(holding.quantity)
                        : '—'}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => onRemove(holding.symbol)}
                    >
                      Remove
                    </Button>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
      <p className={cn('text-sm', totalOk ? 'text-foreground' : 'text-amber-700')}>
        Total {total.toFixed(1)}% / {TARGET_WEIGHT_TOTAL}%
        {!totalOk && ' · Weights must be non-negative and total 100%.'}
      </p>
    </div>
  )
}
