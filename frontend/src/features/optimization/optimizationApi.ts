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
  targetReturn?: number | null
  targetVolatility?: number | null
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
      target_return: request.targetReturn ?? null,
      target_volatility: request.targetVolatility ?? null,
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

export type OptimizationRunParams = {
  tickers: string[]
  start_date: string
  end_date: string
  strategy: string
  max_weight: number | null
  risk_free_rate: number | null
  target_return?: number | null
  target_volatility?: number | null
  initial_capital: number | null
  current_weights: number[] | null
}

export type OptimizationRunSummary = {
  id: string
  portfolio_id: string
  strategy: string
  period_start: string
  period_end: string
  expected_return: number
  volatility: number
  sharpe_ratio: number
  created_at: string
}

export type OptimizationRunDetail = {
  id: string
  portfolio_id: string
  params: OptimizationRunParams
  result: OptimizationResult
  created_at: string
}

export async function saveOptimizationRun(
  portfolioId: string,
  params: OptimizationRunParams,
  result: OptimizationResult,
  token: string,
): Promise<OptimizationRunDetail> {
  return fetchJson(`/api/portfolios/${encodeURIComponent(portfolioId)}/optimization-runs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ params, result }),
  })
}

export async function listOptimizationRuns(
  portfolioId: string,
  token: string,
  limit = 20,
): Promise<OptimizationRunSummary[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  return fetchJson(
    `/api/portfolios/${encodeURIComponent(portfolioId)}/optimization-runs?${params}`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
}

export async function readOptimizationRun(
  portfolioId: string,
  runId: string,
  token: string,
): Promise<OptimizationRunDetail> {
  return fetchJson(
    `/api/portfolios/${encodeURIComponent(portfolioId)}/optimization-runs/${encodeURIComponent(runId)}`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
}
