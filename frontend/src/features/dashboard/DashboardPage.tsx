import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const kpis = [
  { label: 'Total value', value: '$248,500', note: 'Illustrative notional' },
  { label: 'Assets', value: '4', note: 'Stocks + ETFs' },
  { label: 'Expected return', value: '8.4%', note: 'Annualized sample' },
  { label: 'Sharpe ratio', value: '0.31', note: 'Sample period' },
]

const weights = [
  { symbol: 'AAPL', name: 'Apple Inc.', weight: '30%' },
  { symbol: 'MSFT', name: 'Microsoft Corp.', weight: '22%' },
  { symbol: 'VTI', name: 'Vanguard Total Stock', weight: '35%' },
  { symbol: 'AGG', name: 'iShares Core Aggregate', weight: '13%' },
]

const comparison = [
  { metric: 'Annualized return', current: '7.1%', optimized: '8.4%', delta: '+1.3%' },
  { metric: 'Annualized volatility', current: '14.2%', optimized: '12.6%', delta: '−1.6%' },
  { metric: 'Sharpe ratio', current: '0.22', optimized: '0.31', delta: '+0.09' },
]

export default function DashboardPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">Portfolio optimization overview</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Review the current allocation, compare it with an optimized blueprint, and inspect risk
            and return for the selected historical period.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Illustrative sample · As of 13 Oct 2026 · No live optimization run yet
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Select defaultValue="sample">
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Portfolio" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sample">Sample portfolio</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline">Import blueprint</Button>
          <Button>Run analysis</Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <Card key={kpi.label} size="sm">
            <CardHeader>
              <CardDescription className="text-xs tracking-wide uppercase">{kpi.label}</CardDescription>
              <CardTitle className="text-2xl">{kpi.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">{kpi.note}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>Analysis summary</CardTitle>
                <CardDescription>Selected assets and current weights</CardDescription>
              </div>
              <Badge variant="secondary">Sample</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Weight</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {weights.map((row) => (
                  <TableRow key={row.symbol}>
                    <TableCell className="font-medium">{row.symbol}</TableCell>
                    <TableCell className="text-muted-foreground">{row.name}</TableCell>
                    <TableCell>{row.weight}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>Current vs optimized</CardTitle>
                <CardDescription>Aligned metrics for the sample period</CardDescription>
              </div>
              <Badge variant="secondary">Preview</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metric</TableHead>
                  <TableHead>Current</TableHead>
                  <TableHead>Optimized</TableHead>
                  <TableHead>Diff</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {comparison.map((row) => (
                  <TableRow key={row.metric}>
                    <TableCell>{row.metric}</TableCell>
                    <TableCell>{row.current}</TableCell>
                    <TableCell>{row.optimized}</TableCell>
                    <TableCell className="text-muted-foreground">{row.delta}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Risk versus return</CardTitle>
            <CardDescription>Scatter placeholder until chart data is wired</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="relative h-64 rounded-md border border-dashed border-border bg-muted/40">
              <div className="absolute inset-x-10 top-10 bottom-10 border-b border-l border-border">
                <span className="absolute top-8 left-[55%] size-3 rounded-full bg-primary" title="Current" />
                <span
                  className="absolute top-16 left-[40%] size-3 rounded-full bg-muted-foreground"
                  title="Optimized"
                />
              </div>
              <p className="absolute right-0 bottom-3 left-0 text-center text-xs text-muted-foreground">
                Volatility →
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Allocation details</CardTitle>
            <CardDescription>Current weights by asset</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {weights.map((row) => (
              <div key={row.symbol}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{row.symbol}</span>
                  <span className="text-muted-foreground">{row.weight}</span>
                </div>
                <div className="h-2 rounded bg-muted">
                  <div className="h-2 rounded bg-primary" style={{ width: row.weight }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Analysis notes</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            This dashboard shows wireframe layout and illustrative numbers. Connect optimization and
            calculation APIs to replace sample metrics with live results from Portfolio setup.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
