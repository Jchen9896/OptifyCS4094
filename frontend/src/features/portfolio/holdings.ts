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

export function quantityFromWeight(
  weightPercent: number,
  initialValue: number,
  lastClose: number,
): number {
  if (!(initialValue > 0) || !(lastClose > 0) || !Number.isFinite(weightPercent)) {
    return 0
  }
  return ((weightPercent / 100) * initialValue) / lastClose
}

export function addHolding(
  holdings: Holding[],
  next: Omit<Holding, 'weightPercent' | 'quantity'>,
): Holding[] {
  if (holdings.some((holding) => holding.symbol === next.symbol)) {
    return holdings
  }
  return [...holdings, { ...next, weightPercent: 0, quantity: 0 }]
}

export function removeHolding(holdings: Holding[], symbol: string): Holding[] {
  return holdings.filter((holding) => holding.symbol !== symbol)
}

export function updateHoldingWeight(
  holdings: Holding[],
  symbol: string,
  weightPercent: number,
  initialValue: number,
  prices: Record<string, number>,
): Holding[] {
  const safeWeight = Number.isFinite(weightPercent) ? Math.max(0, weightPercent) : 0
  return holdings.map((holding) => {
    if (holding.symbol !== symbol) {
      return holding
    }
    const price = prices[holding.symbol]
    const quantity =
      typeof price === 'number' && price > 0
        ? quantityFromWeight(safeWeight, initialValue, price)
        : 0
    return { ...holding, weightPercent: safeWeight, quantity }
  })
}

/** Re-derive share quantities from weights when initial value or prices change. */
export function resyncQuantities(
  holdings: Holding[],
  initialValue: number,
  prices: Record<string, number>,
): Holding[] {
  return holdings.map((holding) => {
    const price = prices[holding.symbol]
    if (!(typeof price === 'number' && price > 0) || !(initialValue > 0)) {
      return { ...holding, quantity: 0 }
    }
    return {
      ...holding,
      quantity: quantityFromWeight(holding.weightPercent, initialValue, price),
    }
  })
}
