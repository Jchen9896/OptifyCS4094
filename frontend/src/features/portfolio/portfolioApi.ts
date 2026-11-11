import { fetchJson } from '../../lib/apiClient.ts'
import { weightsAreComplete } from './holdings.ts'
import type { Holding } from './types.ts'

export type PortfolioSummary = {
  id: string
  user_id: string
  name: string
  created_at: string
}

type PortfolioSetup = {
  initial_capital: number
  start_date: string
  end_date: string
  strategy: string
  max_weight: number
  risk_free_rate: number
  target_return?: number | null
  target_volatility?: number | null
  weights: Record<string, number>
  reference_prices: Record<string, number>
  quote_types?: Record<string, string> | null
}

export type SavedPortfolio = PortfolioSummary & {
  holdings: { symbol: string; name: string; quantity: string }[]
  setup: PortfolioSetup | null
}

export type PortfolioDraft = {
  portfolioName: string
  initialCapital: number
  startDate: string
  endDate: string
  strategy: string
  maxWeightPercent: number
  riskFreePercent: number
  targetReturnPercent: number | null
  targetVolatilityPercent: number | null
  holdings: Holding[]
  referencePrices: Record<string, number>
}

export function buildPortfolioRequest(draft: PortfolioDraft) {
  const name = draft.portfolioName.trim()
  if (!name) throw new Error('Enter a portfolio name.')
  if (!(Number.isFinite(draft.initialCapital) && draft.initialCapital > 0)) {
    throw new Error('Enter a positive initial portfolio value.')
  }
  if (!draft.startDate || !draft.endDate || draft.startDate >= draft.endDate) {
    throw new Error('Choose a start date before the end date.')
  }
  if (!(draft.maxWeightPercent > 0 && draft.maxWeightPercent <= 100) || !Number.isFinite(draft.riskFreePercent)) {
    throw new Error('Check the maximum weight and risk-free rate.')
  }
  if (draft.holdings.length > 0 && !weightsAreComplete(draft.holdings)) {
    throw new Error('Set allocation weights to 100% before saving.')
  }
  const weights: Record<string, number> = {}
  const prices: Record<string, number> = {}
  const quoteTypes: Record<string, string> = {}
  const holdings = draft.holdings.map((holding) => {
    const quantity = holding.quantity.toFixed(6)
    const price = draft.referencePrices[holding.symbol]
    if (!(Number.isFinite(holding.weightPercent) && holding.weightPercent > 0 && holding.weightPercent <= 100) ||
        !(Number.isFinite(price) && price > 0) ||
        !(Number.isFinite(holding.quantity) && Number(quantity) > 0 && Number(quantity) < 1e12)) {
      throw new Error('Give each asset a positive weight. Prices must load successfully so quantities stay within 12 whole digits and 6 decimal places.')
    }
    weights[holding.symbol] = holding.weightPercent
    prices[holding.symbol] = price
    if (holding.quoteType) quoteTypes[holding.symbol] = holding.quoteType
    return { symbol: holding.symbol, quantity }
  })
  return {
    name,
    holdings,
    setup: {
      initial_capital: draft.initialCapital,
      start_date: draft.startDate,
      end_date: draft.endDate,
      strategy: draft.strategy,
      max_weight: draft.maxWeightPercent / 100,
      risk_free_rate: draft.riskFreePercent / 100,
      target_return:
        draft.targetReturnPercent == null ? null : draft.targetReturnPercent / 100,
      target_volatility:
        draft.targetVolatilityPercent == null ? null : draft.targetVolatilityPercent / 100,
      weights,
      reference_prices: prices,
      quote_types: Object.keys(quoteTypes).length > 0 ? quoteTypes : null,
    },
  }
}

export function listPortfolios(token: string): Promise<PortfolioSummary[]> {
  return fetchJson('/api/portfolios', { headers: { Authorization: `Bearer ${token}` } })
}

export function readPortfolio(token: string, id: string): Promise<SavedPortfolio> {
  return fetchJson(`/api/portfolios/${encodeURIComponent(id)}`, { headers: { Authorization: `Bearer ${token}` } })
}

export function createPortfolio(token: string, draft: PortfolioDraft): Promise<SavedPortfolio> {
  return fetchJson('/api/portfolios', {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(buildPortfolioRequest(draft)),
  })
}

export async function deletePortfolio(token: string, id: string): Promise<void> {
  await fetchJson<Record<string, never>>(`/api/portfolios/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export function restorePortfolio(saved: SavedPortfolio): PortfolioDraft {
  const setup = saved.setup
  if (!setup) throw new Error('This portfolio has no saved setup inputs. Its holdings are available through the portfolio API.')
  return {
    portfolioName: saved.name,
    initialCapital: setup.initial_capital,
    startDate: setup.start_date,
    endDate: setup.end_date,
    strategy: setup.strategy,
    maxWeightPercent: setup.max_weight * 100,
    riskFreePercent: setup.risk_free_rate * 100,
    targetReturnPercent:
      setup.target_return == null ? null : setup.target_return * 100,
    targetVolatilityPercent:
      setup.target_volatility == null ? null : setup.target_volatility * 100,
    referencePrices: setup.reference_prices,
    holdings: saved.holdings.map((holding) => ({
      symbol: holding.symbol,
      name: holding.name,
      quoteType: setup.quote_types?.[holding.symbol] ?? null,
      quantity: Number(holding.quantity),
      weightPercent: setup.weights[holding.symbol],
    })),
  }
}
