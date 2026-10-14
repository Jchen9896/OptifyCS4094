/** One asset in the local portfolio setup (weights match the wireframe). */
export type Holding = {
  symbol: string
  name: string
  quoteType: string | null
  weightPercent: number
}

export const TARGET_WEIGHT_TOTAL = 100
