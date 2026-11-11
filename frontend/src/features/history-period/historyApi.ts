import { ApiError, fetchJson } from '../../lib/apiClient.ts'

export type PriceHistoryRequest = {
  symbol: string
  startDate: string
  endDate: string
}

export type PriceHistoryResponse = {
  symbol: string
  start_date: string
  end_date: string
  bar_count: number
  first_date: string | null
  last_date: string | null
  last_close: number | null
  source: string
  fetched_at: string | null
  served_from_database: boolean
}

export async function fetchPriceHistory(
  request: PriceHistoryRequest,
): Promise<PriceHistoryResponse> {
  return fetchJson<PriceHistoryResponse>('/api/market-data/history', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      symbol: request.symbol,
      start_date: request.startDate,
      end_date: request.endDate,
    }),
  })
}

/** Load or refresh stored bars for each symbol. Returns last closes for quantity estimates. */
export async function ensureHoldingsPrices(
  symbols: string[],
  startDate: string,
  endDate: string,
): Promise<Record<string, number>> {
  if (symbols.length === 0) {
    throw new Error('Add at least one asset before loading prices.')
  }
  if (!startDate || !endDate || startDate >= endDate) {
    throw new Error('Choose a start date before the end date.')
  }
  const prices: Record<string, number> = {}
  for (const symbol of symbols) {
    try {
      const result = await fetchPriceHistory({ symbol, startDate, endDate })
      if (result.last_close == null || !(result.last_close > 0)) {
        throw new Error(`No usable last close for ${symbol}.`)
      }
      prices[symbol] = result.last_close
    } catch (caught) {
      if (caught instanceof ApiError) {
        throw new Error(`${symbol}: ${caught.code}: ${caught.message}`)
      }
      throw caught
    }
  }
  return prices
}
