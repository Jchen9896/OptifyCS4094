export type HealthResponse = {
  status: string
  api: string
  database: string
  checked_at: string
}

export type ApiErrorBody = {
  detail?: { code?: string; message?: string } | string
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(message: string, code: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  const body = (await response.json().catch(() => ({}))) as ApiErrorBody

  if (!response.ok) {
    const detail = body.detail
    if (typeof detail === 'object' && detail !== null) {
      throw new ApiError(detail.message ?? `Request failed (${response.status})`, detail.code ?? 'app_error', response.status)
    }
    throw new ApiError(
      typeof detail === 'string' ? detail : `Request failed (${response.status})`,
      'app_error',
      response.status,
    )
  }

  return body as T
}

export async function getHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>('/api/health')
}
