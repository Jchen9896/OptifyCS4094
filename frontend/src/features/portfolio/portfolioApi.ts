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
  weights: Record<string, number>
  reference_prices: Record<string, number>
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
  holdings: Holding[]
  referencePrices: Record<string, number>
}

function ownerQuery(userId: string): string {
  const value = userId.trim()
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error('Enter an existing user UUID. Sign-in is not available yet.')
  }
  return `user_id=${encodeURIComponent(value)}`
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
  const holdings = draft.holdings.map((holding) => {
    const quantity = holding.quantity.toFixed(6)
    const price = draft.referencePrices[holding.symbol]
    if (!(Number.isFinite(holding.weightPercent) && holding.weightPercent > 0 && holding.weightPercent <= 100) ||
        !(Number.isFinite(price) && price > 0) ||
        !(Number.isFinite(holding.quantity) && Number(quantity) > 0 && Number(quantity) < 1e12)) {
      throw new Error('Give each asset a positive weight and load prices before saving. Quantities need at most 12 whole digits and 6 decimal places.')
    }
    weights[holding.symbol] = holding.weightPercent
    prices[holding.symbol] = price
    return { symbol: holding.symbol, quantity }
  })
  return { name, holdings, setup: {
    initial_capital: draft.initialCapital, start_date: draft.startDate, end_date: draft.endDate,
    strategy: draft.strategy, max_weight: draft.maxWeightPercent / 100,
    risk_free_rate: draft.riskFreePercent / 100, weights, reference_prices: prices,
  } }
}

export function listPortfolios(userId: string): Promise<PortfolioSummary[]> {
  return fetchJson(`/api/portfolios?${ownerQuery(userId)}`)
}

export function readPortfolio(userId: string, id: string): Promise<SavedPortfolio> {
  return fetchJson(`/api/portfolios/${encodeURIComponent(id)}?${ownerQuery(userId)}`)
}

export function createPortfolio(userId: string, draft: PortfolioDraft): Promise<SavedPortfolio> {
  const query = ownerQuery(userId)
  return fetchJson(`/api/portfolios?${query}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildPortfolioRequest(draft)),
  })
}

export function restorePortfolio(saved: SavedPortfolio): PortfolioDraft {
  const setup = saved.setup
  if (!setup) throw new Error('This portfolio has no saved setup inputs. Its holdings are available through the portfolio API.')
  return {
    portfolioName: saved.name, initialCapital: setup.initial_capital,
    startDate: setup.start_date, endDate: setup.end_date, strategy: setup.strategy,
    maxWeightPercent: setup.max_weight * 100, riskFreePercent: setup.risk_free_rate * 100,
    referencePrices: setup.reference_prices,
    holdings: saved.holdings.map((holding) => ({
      symbol: holding.symbol, name: holding.name, quoteType: null,
      quantity: Number(holding.quantity), weightPercent: setup.weights[holding.symbol],
    })),
  }
}
