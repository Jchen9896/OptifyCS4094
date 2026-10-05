export type HealthResponse = {
  status: string
  api: string
  database: string
  checked_at: string
}

export type ApiErrorBody = {
  detail?: { code?: string; message?: string } | string
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health')
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody
    const detail = body.detail
    const message =
      typeof detail === 'string' ? detail : detail?.message ?? `Health check failed (${response.status})`
    throw new Error(message)
  }
  return (await response.json()) as HealthResponse
}
