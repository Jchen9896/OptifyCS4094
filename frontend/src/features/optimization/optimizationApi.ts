import { fetchJson } from '../../lib/apiClient.ts'
import type { Holding } from '../portfolio/types.ts'

export type OptimizationRequest = {
  tickers: string[]
  startDate: string
  endDate: string
  strategy: string
  maxWeight: number | null
  riskFreeRate: number | null
  currentWeights: number[]
  initialCapital: number | null
}

export type EquityCurvePoint = {
  date: string
  current_value: number
  optimized_value: number
}

export type OptimizationResult = {
  strategy: string
  weights: Record<string, number>
  expected_return: number
  volatility: number
  sharpe_ratio: number
  current_expected_return: number
  current_volatility: number
  current_sharpe_ratio: number
  period_start: string
  period_end: string
  assumptions: string[]
  initial_capital: number
  equity_curve: EquityCurvePoint[]
}

export type StoredOptimizationRun = {
  result: OptimizationResult
  holdings: Holding[]
  portfolioName: string
  referencePrices: Record<string, number>
  initialCapital: number
  portfolioId?: string | null
  /** Optional note when auto-save was skipped or failed. */
  saveNote?: string | null
}

function lastRunKey(userId: string | null, portfolioId: string | null): string {
  return `optify.lastOptimization.${userId ?? 'guest'}.${portfolioId ?? 'new'}`
}

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
      current_weights: request.currentWeights,
      initial_capital: request.initialCapital,
    }),
  })
}

export function saveLastOptimizationRun(
  run: StoredOptimizationRun,
  userId: string | null,
  portfolioId: string | null = null,
): void {
  const id = portfolioId ?? run.portfolioId ?? null
  sessionStorage.setItem(lastRunKey(userId, id), JSON.stringify({ ...run, portfolioId: id }))
}

export function loadLastOptimizationRun(
  userId: string | null,
  portfolioId: string | null = null,
): StoredOptimizationRun | null {
  const raw = sessionStorage.getItem(lastRunKey(userId, portfolioId))
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw) as StoredOptimizationRun
  } catch {
    return null
  }
}

export function clearLastOptimizationRun(
  userId: string | null,
  portfolioId: string | null = null,
): void {
  sessionStorage.removeItem(lastRunKey(userId, portfolioId))
}
