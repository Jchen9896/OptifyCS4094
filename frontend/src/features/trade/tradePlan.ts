export type TradeSide = 'buy' | 'sell' | 'hold'

export type PlannedTrade = {
  symbol: string
  name: string
  side: TradeSide
  currentQty: number
  targetQty: number
  deltaQty: number
  price: number | null
  estimatedNotional: number | null
  currentWeight: number
  targetWeight: number
}

export function sharesForWeight(
  weight: number,
  capital: number,
  price: number | undefined,
): number | null {
  if (!(typeof price === 'number' && price > 0 && capital > 0 && Number.isFinite(weight))) {
    return null
  }
  return (weight * capital) / price
}

/** Whole shares only — Schwab equity market orders reject fractional qty. */
export function wholeShares(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.round(value))
}

/** Round share deltas to whole shares; zero after rounding collapses to hold. */
export function plannedTradesFromWeights(input: {
  symbols: string[]
  names: Record<string, string>
  currentWeights: Record<string, number>
  targetWeights: Record<string, number>
  currentQuantities: Record<string, number>
  prices: Record<string, number>
  capital: number
}): PlannedTrade[] {
  const { symbols, names, currentWeights, targetWeights, currentQuantities, prices, capital } =
    input
  return symbols
    .map((symbol) => {
      const price = prices[symbol]
      const currentWeight = currentWeights[symbol] ?? 0
      const targetWeight = targetWeights[symbol] ?? 0
      const storedQty = currentQuantities[symbol]
      const rawCurrent =
        typeof storedQty === 'number' && storedQty > 0
          ? storedQty
          : (sharesForWeight(currentWeight, capital, price) ?? 0)
      const currentQty = wholeShares(rawCurrent)
      const targetQty = wholeShares(sharesForWeight(targetWeight, capital, price) ?? 0)
      const deltaQty = targetQty - currentQty
      const side: TradeSide = deltaQty > 0 ? 'buy' : deltaQty < 0 ? 'sell' : 'hold'
      const estimatedNotional =
        typeof price === 'number' && price > 0 ? Math.abs(deltaQty) * price : null
      return {
        symbol,
        name: names[symbol] ?? symbol,
        side,
        currentQty,
        targetQty,
        deltaQty,
        price: typeof price === 'number' && price > 0 ? price : null,
        estimatedNotional,
        currentWeight,
        targetWeight,
      }
    })
    .sort((a, b) => Math.abs(b.deltaQty) - Math.abs(a.deltaQty))
}

export function summarizeTrades(trades: PlannedTrade[]): {
  buys: number
  sells: number
  holds: number
  buyNotional: number
  sellNotional: number
} {
  let buys = 0
  let sells = 0
  let holds = 0
  let buyNotional = 0
  let sellNotional = 0
  for (const trade of trades) {
    if (trade.side === 'buy') {
      buys += 1
      buyNotional += trade.estimatedNotional ?? 0
    } else if (trade.side === 'sell') {
      sells += 1
      sellNotional += trade.estimatedNotional ?? 0
    } else {
      holds += 1
    }
  }
  return { buys, sells, holds, buyNotional, sellNotional }
}
