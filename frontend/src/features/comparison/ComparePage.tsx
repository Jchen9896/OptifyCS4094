import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Field, FieldLabel } from '@/components/ui/field'
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

const metrics = [
  {
    label: 'Annualized return',
    explanation: 'Average yearly return over the shared historical period',
    a: '7.1%',
    b: '8.4%',
    diff: '+1.3 pp',
  },
  {
    label: 'Annualized volatility',
    explanation: 'Risk measured as yearly standard deviation of returns',
    a: '14.2%',
    b: '12.6%',
    diff: '−1.6 pp',
  },
  {
    label: 'Sharpe ratio',
    explanation: 'Return per unit of risk after the risk-free rate',
    a: '0.22',
    b: '0.31',
    diff: '+0.09',
  },
]

const weights = [
  { symbol: 'AAPL', a: '30%', b: '24%', diff: '−6 pp' },
  { symbol: 'MSFT', a: '22%', b: '20%', diff: '−2 pp' },
  { symbol: 'VTI', a: '35%', b: '41%', diff: '+6 pp' },
  { symbol: 'AGG', a: '13%', b: '15%', diff: '+2 pp' },
]

export default function ComparePage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">Compare portfolios</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Place two portfolio versions side by side using the same historical period and
            assumptions.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Illustrative sample · Shared period 13 Oct 2025 – 12 Oct 2026
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button>Refine blueprint</Button>
          <Button>Run analysis</Button>
        </div>
      </div>

      <Card>
        <CardContent className="space-y-4 pt-(--card-spacing)">
          <div className="grid gap-4 md:grid-cols-2">
            <Field>
              <FieldLabel>Portfolio A</FieldLabel>
              <Select defaultValue="current">
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="current">Sample portfolio — current</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel>Portfolio B</FieldLabel>
              <Select defaultValue="optimized">
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="optimized">Sample portfolio — optimized</SelectItem>
                </SelectContent>
              </Select>
            </Field>
          </div>
          <div className="rounded-lg border border-border bg-muted/40 px-3 py-3 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">Historical period</p>
            <p className="mt-1">13 Oct 2025 → 12 Oct 2026 · Daily adjusted closes · Calendar XNYS</p>
            <p className="mt-2 text-xs">
              Data provenance: shared market data from stored price bars when available
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>Aligned metric comparison</CardTitle>
              <CardDescription>Same period and assumptions for both portfolios</CardDescription>
            </div>
            <Badge variant="secondary">Sample</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead>Current</TableHead>
                <TableHead>Optimized</TableHead>
                <TableHead>Difference</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {metrics.map((row) => (
                <TableRow key={row.label}>
                  <TableCell>
                    <p className="font-medium">{row.label}</p>
                    <p className="text-xs text-muted-foreground">{row.explanation}</p>
                  </TableCell>
                  <TableCell className="text-lg font-semibold">{row.a}</TableCell>
                  <TableCell className="text-lg font-semibold">{row.b}</TableCell>
                  <TableCell className="text-muted-foreground">{row.diff}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="mt-3 text-xs text-muted-foreground">
            Positive differences favor the optimized blueprint in this sample.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Historical risk-return profile</CardTitle>
            <CardDescription>Current vs optimized markers</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="relative h-64 rounded-md border border-dashed border-border bg-muted/40">
              <div className="absolute inset-x-12 top-8 bottom-12 border-b border-l border-border">
                <span className="absolute top-20 left-[62%] size-3 rounded-full bg-primary" />
                <span className="absolute top-12 left-[45%] size-3 rounded-full bg-muted-foreground" />
              </div>
              <div className="absolute top-3 left-4 flex gap-4 text-xs text-muted-foreground">
                <span>● Current</span>
                <span>● Optimized</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Historical performance</CardTitle>
            <CardDescription>Cumulative growth placeholder</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="relative h-64 rounded-md border border-dashed border-border bg-muted/40">
              <svg viewBox="0 0 320 160" className="h-full w-full p-4 text-foreground" aria-hidden>
                <polyline
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  points="10,120 60,110 110,90 160,95 210,70 260,60 310,40"
                />
                <polyline
                  fill="none"
                  stroke="oklch(0.556 0 0)"
                  strokeWidth="2"
                  points="10,130 60,125 110,115 160,100 210,85 260,55 310,35"
                />
              </svg>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Asset-level weights</CardTitle>
          <CardDescription>How each holding differs between the two portfolios</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Portfolio A</TableHead>
                <TableHead>Portfolio B</TableHead>
                <TableHead>Difference</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {weights.map((row) => (
                <TableRow key={row.symbol}>
                  <TableCell className="font-medium">{row.symbol}</TableCell>
                  <TableCell>{row.a}</TableCell>
                  <TableCell>{row.b}</TableCell>
                  <TableCell className="text-muted-foreground">{row.diff}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardFooter className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Refine results</CardTitle>
            <CardDescription className="mt-1">
              Adjust the blueprint on Portfolio setup, then return here after analysis is connected.
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button>Refine blueprint</Button>
            <Button disabled>Run analysis</Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
