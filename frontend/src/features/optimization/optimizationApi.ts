import { fetchJson } from '../../lib/apiClient.ts'
import type { Holding } from '../portfolio/types.ts'

export type OptimizationRequest = {
  tickers: string[]
  startDate: string
  endDate: string
  strategy: string
  maxWeight: number | null
  riskFreeRate: number | null
}

export type OptimizationResult = {
  strategy: string
  weights: Record<string, number>
  expected_return: number
  volatility: number
  sharpe_ratio: number
  period_start: string
  period_end: string
  assumptions: string[]
}

export type StoredOptimizationRun = {
  result: OptimizationResult
  holdings: Holding[]
  portfolioName: string
}

const LAST_RUN_KEY = 'optify.lastOptimization'

export async function runOptimization(
  request: OptimizationRequest,
): Promise<OptimizationResult> {
  return fetchJson<OptimizationResult>('/api/optimizations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tickers: request.tickers,
      start_date: request.startDate,
      end_date: request.endDate,
      strategy: request.strategy,
      max_weight: request.maxWeight,
      risk_free_rate: request.riskFreeRate,
    }),
  })
}

export function saveLastOptimizationRun(run: StoredOptimizationRun): void {
  sessionStorage.setItem(LAST_RUN_KEY, JSON.stringify(run))
}

export function loadLastOptimizationRun(): StoredOptimizationRun | null {
  const raw = sessionStorage.getItem(LAST_RUN_KEY)
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw) as StoredOptimizationRun
  } catch {
    return null
  }
}
