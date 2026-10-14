import { fetchJson } from '../../lib/apiClient.ts'

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
