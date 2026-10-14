import { TARGET_WEIGHT_TOTAL, type Holding } from '../types.ts'
import { sumWeights } from '../holdings.ts'

type HoldingsTableProps = {
  holdings: Holding[]
  onWeightChange: (symbol: string, weightPercent: number) => void
  onRemove: (symbol: string) => void
}

export default function HoldingsTable({ holdings, onWeightChange, onRemove }: HoldingsTableProps) {
  const total = sumWeights(holdings)
  const totalOk = Math.abs(total - TARGET_WEIGHT_TOTAL) < 0.01

  if (holdings.length === 0) {
    return <p className="text-sm text-muted">No assets yet. Search and add a ticker above.</p>
  }

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-line bg-ink text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Symbol</th>
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 font-medium">Type</th>
              <th className="px-3 py-2 font-medium">Weight (%)</th>
              <th className="px-3 py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {holdings.map((holding) => (
              <tr key={holding.symbol} className="border-b border-line last:border-0">
                <td className="px-3 py-2 font-medium text-paper">{holding.symbol}</td>
                <td className="px-3 py-2 text-muted">{holding.name}</td>
                <td className="px-3 py-2 text-muted">{holding.quoteType ?? '—'}</td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    className="w-24 rounded-md border border-line bg-ink px-2 py-1 text-paper"
                    value={holding.weightPercent}
                    onChange={(event) =>
                      onWeightChange(holding.symbol, Number(event.target.value))
                    }
                  />
                </td>
                <td className="px-3 py-2 text-right">
                  <button
                    type="button"
                    className="text-danger hover:underline"
                    onClick={() => onRemove(holding.symbol)}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className={`text-sm ${totalOk ? 'text-mint' : 'text-warn'}`}>
        Total {total.toFixed(1)}% / {TARGET_WEIGHT_TOTAL}%
        {!totalOk && ' · Weights must be non-negative and total 100%.'}
      </p>
    </div>
  )
}
