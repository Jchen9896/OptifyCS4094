import { fetchJson } from '../../lib/apiClient.ts'

export type SchwabAccountSummary = {
  account_number: string
  account_hash: string
}

export type TradeOrderLeg = {
  symbol: string
  side: 'buy' | 'sell'
  quantity: number
}

export type SubmittedOrderResult = {
  symbol: string
  side: 'buy' | 'sell'
  quantity: number
  status: 'accepted' | 'rejected'
  order_id: string | null
  message: string | null
}

export type SubmitSchwabOrdersResponse = {
  account_hash: string
  account_number: string | null
  results: SubmittedOrderResult[]
}

export function listSchwabTradeAccounts(token: string): Promise<SchwabAccountSummary[]> {
  return fetchJson('/api/trade/schwab/accounts', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

export function submitSchwabOrders(
  token: string,
  body: { account_hash?: string | null; orders: TradeOrderLeg[] },
): Promise<SubmitSchwabOrdersResponse> {
  return fetchJson('/api/trade/schwab/orders', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
}
