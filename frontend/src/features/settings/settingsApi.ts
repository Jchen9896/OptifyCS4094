import { fetchJson } from '../../lib/apiClient.ts'
import type { BrokerageId } from '../portfolio/brokerageImport.ts'

export type BrokerageCredentialStatus = {
  provider: BrokerageId
  callback_url: string
  app_key_hint: string
  updated_at: string
  authorized: boolean
}

export type BrokerageCredentialUpsert = {
  app_key: string
  app_secret: string
  callback_url?: string
}

export type SchwabOAuthSetup = {
  callback_url: string
  frontend_redirect_url: string
}

export type SchwabAuthorizeResponse = {
  authorize_url: string
}

/** Wipe local Optify data for the signed-in user. Clerk deletion is separate. */
export async function deleteLocalAccount(token: string): Promise<void> {
  await fetchJson<Record<string, never>>('/api/account', {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export function listBrokerageCredentials(token: string): Promise<BrokerageCredentialStatus[]> {
  return fetchJson('/api/brokerage-credentials', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

export function getSchwabOAuthSetup(token?: string | null): Promise<SchwabOAuthSetup> {
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  return fetchJson('/api/brokerage-credentials/schwab/setup', { headers })
}

export function startSchwabAuthorize(token: string): Promise<SchwabAuthorizeResponse> {
  return fetchJson('/api/brokerage-credentials/schwab/authorize', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export function upsertBrokerageCredentials(
  token: string,
  provider: BrokerageId,
  body: BrokerageCredentialUpsert,
): Promise<BrokerageCredentialStatus> {
  return fetchJson(`/api/brokerage-credentials/${encodeURIComponent(provider)}`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
}

export async function deleteBrokerageCredentials(
  token: string,
  provider: BrokerageId,
): Promise<void> {
  await fetchJson<Record<string, never>>(
    `/api/brokerage-credentials/${encodeURIComponent(provider)}`,
    {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    },
  )
}
