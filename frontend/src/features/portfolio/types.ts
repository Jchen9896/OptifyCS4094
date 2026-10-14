/** One asset in the local portfolio setup (weights match the wireframe). */
export type Holding = {
  symbol: string
  name: string
  quoteType: string | null
  weightPercent: number
  /** Derived from weight × initial portfolio value / last close when prices are loaded. */
  quantity: number
}

export const TARGET_WEIGHT_TOTAL = 100
