import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { formatWeight } from '@/lib/formatters.ts'
import type { EquityCurvePoint } from '../optimization/optimizationApi.ts'

type WeightRow = {
  symbol: string
  current: number
  optimized: number
}

type PortfolioPerformanceChartsProps = {
  equityCurve: EquityCurvePoint[]
  initialCapital: number
  weightRows: WeightRow[]
}

const capitalConfig = {
  current: { label: 'Current portfolio', color: 'var(--chart-2)' },
  optimized: { label: 'Optimized portfolio', color: 'var(--chart-1)' },
} satisfies ChartConfig

const weightConfig = {
  current: { label: 'Current weight', color: 'var(--chart-2)' },
  optimized: { label: 'Optimized weight', color: 'var(--chart-1)' },
} satisfies ChartConfig

function formatCurrency(value: number): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

export default function PortfolioPerformanceCharts({
  equityCurve,
  initialCapital,
  weightRows,
}: PortfolioPerformanceChartsProps) {
  const capitalData = equityCurve.map((point) => ({
    date: point.date,
    current: point.current_value,
    optimized: point.optimized_value,
  }))
  const weightData = weightRows.map((row) => ({
    symbol: row.symbol,
    current: row.current * 100,
    optimized: row.optimized * 100,
  }))

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Portfolio capital over time</CardTitle>
          <CardDescription>
            Buy-and-hold path from {formatCurrency(initialCapital)} using current vs optimized
            weights on shared trading days.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={capitalConfig} className="aspect-auto h-72 w-full">
            <LineChart accessibilityLayer data={capitalData} margin={{ left: 12, right: 12 }}>
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                minTickGap={32}
                tickFormatter={(value: string) => value.slice(5)}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={72}
                tickFormatter={(value: number) => formatCurrency(value)}
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    labelFormatter={(value) => String(value)}
                    formatter={(value) => formatCurrency(Number(value))}
                  />
                }
              />
              <ChartLegend content={<ChartLegendContent />} />
              <Line
                type="monotone"
                dataKey="current"
                stroke="var(--color-current)"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="optimized"
                stroke="var(--color-optimized)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ChartContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Weights before and after</CardTitle>
          <CardDescription>Current allocation versus optimized weights by symbol.</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={weightConfig} className="aspect-auto h-64 w-full">
            <BarChart accessibilityLayer data={weightData} margin={{ left: 12, right: 12 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="symbol" tickLine={false} axisLine={false} />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={40}
                tickFormatter={(value: number) => `${value}%`}
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    formatter={(value) => formatWeight(Number(value) / 100)}
                  />
                }
              />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar dataKey="current" fill="var(--color-current)" radius={4} />
              <Bar dataKey="optimized" fill="var(--color-optimized)" radius={4} />
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>
    </div>
  )
}
