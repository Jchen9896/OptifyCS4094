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

export async function downloadAccountExport(token: string): Promise<void> {
  const response = await fetch('/api/account/export', {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: { message?: string } | string
    }
    const detail = body.detail
    const message =
      typeof detail === 'object' && detail?.message
        ? detail.message
        : typeof detail === 'string' && detail
          ? detail
          : `Could not download data (${response.status}).`
    throw new Error(message)
  }
  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const match = /filename="([^"]+)"/.exec(disposition)
  const filename =
    match?.[1] ?? `optify-export-${new Date().toISOString().slice(0, 10)}.json`
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
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
