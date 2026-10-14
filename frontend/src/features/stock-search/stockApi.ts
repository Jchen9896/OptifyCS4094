import { fetchJson } from '../../lib/apiClient.ts'

export type StockSearchResult = {
  symbol: string
  name: string
  exchange: string | null
  quote_type: string | null
}

export type StockSearchResponse = {
  query: string
  results: StockSearchResult[]
}

export async function searchStocks(query: string): Promise<StockSearchResponse> {
  const params = new URLSearchParams({ q: query })
  return fetchJson<StockSearchResponse>(`/api/stocks?${params.toString()}`)
}
