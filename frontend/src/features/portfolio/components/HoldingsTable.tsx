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
  onWeightChange: (symbol: string, weightPercent: number) => void
  onRemove: (symbol: string) => void
}

export default function HoldingsTable({ holdings, onWeightChange, onRemove }: HoldingsTableProps) {
  const total = sumWeights(holdings)
  const totalOk = Math.abs(total - TARGET_WEIGHT_TOTAL) < 0.01

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
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {holdings.map((holding) => (
              <TableRow key={holding.symbol}>
                <TableCell className="font-medium">{holding.symbol}</TableCell>
                <TableCell className="text-muted-foreground">{holding.name}</TableCell>
                <TableCell className="text-muted-foreground">{holding.quoteType ?? '—'}</TableCell>
                <TableCell>
                  <Input
                    type="number"
                    min={0}
                    step={0.1}
                    className="w-24"
                    value={holding.weightPercent}
                    onChange={(event) =>
                      onWeightChange(holding.symbol, Number(event.target.value))
                    }
                  />
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
            ))}
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
