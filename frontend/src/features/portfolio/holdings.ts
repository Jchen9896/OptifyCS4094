import { TARGET_WEIGHT_TOTAL, type Holding } from './types.ts'

export function sumWeights(holdings: Holding[]): number {
  return holdings.reduce((total, holding) => total + holding.weightPercent, 0)
}

export function weightsAreComplete(holdings: Holding[]): boolean {
  if (holdings.length === 0) {
    return false
  }
  return Math.abs(sumWeights(holdings) - TARGET_WEIGHT_TOTAL) < 0.01
}

export function addHolding(holdings: Holding[], next: Omit<Holding, 'weightPercent'>): Holding[] {
  if (holdings.some((holding) => holding.symbol === next.symbol)) {
    return holdings
  }
  return [...holdings, { ...next, weightPercent: 0 }]
}

export function removeHolding(holdings: Holding[], symbol: string): Holding[] {
  return holdings.filter((holding) => holding.symbol !== symbol)
}

export function updateHoldingWeight(
  holdings: Holding[],
  symbol: string,
  weightPercent: number,
): Holding[] {
  const safeWeight = Number.isFinite(weightPercent) ? Math.max(0, weightPercent) : 0
  return holdings.map((holding) =>
    holding.symbol === symbol ? { ...holding, weightPercent: safeWeight } : holding,
  )
}
