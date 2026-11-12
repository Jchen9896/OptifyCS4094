import { z } from 'zod'
import { categoriesSchema, postSchema, postPageSchema, replySchema, replyPageSchema } from './communitySchemas'
import type { PostInput } from './communitySchemas'

export class CommunityError extends Error {
  readonly kind: 'session' | 'missing' | 'validation' | 'cursor' | 'unavailable' | 'invalid'
  readonly uncertain: boolean
  constructor(kind: CommunityError['kind'], message: string, uncertain = false) {
    super(message)
    this.kind = kind
    this.uncertain = uncertain
  }
}

export function errorMessage(error: unknown, write = false): string {
  const message = error instanceof CommunityError ? error.message : 'Community is unavailable. Please try again.'
  return write && (!(error instanceof CommunityError) || error.uncertain || !['validation', 'missing', 'session'].includes(error.kind))
    ? message + ' The write may have completed. Check the discussion before submitting again. Your draft is kept.'
    : message
}

export function createCommunityApi({
  getToken, fetcher = fetch,
}: { getToken: () => Promise<string | null>; fetcher?: typeof fetch }) {
  const lifetime = new AbortController()
  let expired = false
  function check(signal: AbortSignal, writeStarted = false) {
    signal.throwIfAborted()
    lifetime.signal.throwIfAborted()
    if (expired) throw new CommunityError('session', 'Your session has expired. Sign in to continue.', writeStarted)
  }
  async function request<T>(path: string, schema: z.ZodType<T>, signal: AbortSignal, method = 'GET', body?: unknown): Promise<T> {
    check(signal)
    const token = await getToken()
    check(signal)
    if (!token) {
      expired = true
      throw new CommunityError('session', 'Your session has expired. Sign in to continue.')
    }
    const response = await fetcher('/api/community' + path, {
      method, signal: AbortSignal.any([signal, lifetime.signal]),
      headers: { Authorization: 'Bearer ' + token, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    })
    check(signal, method !== 'GET')
    if (!response.ok) {
      let code: unknown
      try {
        const value: unknown = await response.json()
        const parsed = z.object({ detail: z.object({ code: z.string() }) }).safeParse(value)
        code = parsed.success ? parsed.data.detail.code : undefined
      } catch {}
      check(signal, method !== 'GET')
      if (response.status === 401) {
        expired = true
        throw new CommunityError('session', 'Your session has expired. Sign in to continue.')
      }
      if (response.status === 404) throw new CommunityError('missing', 'This item is unavailable or you no longer have access.')
      if (code === 'invalid_cursor') throw new CommunityError('cursor', 'This page has expired. Reload the list.')
      if (response.status === 422) throw new CommunityError('validation', 'Check the category and text limits, then try again.')
      throw new CommunityError('unavailable', 'Community is unavailable. Please try again.')
    }
    let data: unknown
    try { data = response.status === 204 ? undefined : await response.json() }
    catch { throw new CommunityError('invalid', 'Community returned an invalid response. Please reload.') }
    check(signal, method !== 'GET')
    const result = schema.safeParse(data)
    if (!result.success) throw new CommunityError('invalid', 'Community returned an invalid response. Please reload.')
    return result.data
  }
  function query(values: Record<string, string | null | undefined>) {
    const params = new URLSearchParams()
    for (const [key, value] of Object.entries(values)) if (value) params.set(key, value)
    const text = params.toString()
    return text ? '?' + text : ''
  }
  return {
    dispose: () => lifetime.abort(),
    categories: (signal: AbortSignal) => request('/categories', categoriesSchema, signal),
    posts: (category: string, cursor: string | null, signal: AbortSignal) =>
      request('/posts' + query({ category, cursor }), postPageSchema, signal),
    post: (id: string, signal: AbortSignal) => request('/posts/' + encodeURIComponent(id), postSchema, signal),
    createPost: (input: PostInput, signal: AbortSignal) => request('/posts', postSchema, signal, 'POST', { title: input.title, body: input.body, category: input.category }),
    updatePost: (id: string, input: PostInput, signal: AbortSignal) =>
      request('/posts/' + encodeURIComponent(id), postSchema, signal, 'PATCH', { title: input.title, body: input.body, category: input.category }),
    deletePost: (id: string, signal: AbortSignal) =>
      request('/posts/' + encodeURIComponent(id), z.undefined(), signal, 'DELETE'),
    replies: (id: string, parent: string | null, cursor: string | null, signal: AbortSignal) =>
      request('/posts/' + encodeURIComponent(id) + '/replies' + query({ parent_reply_id: parent, cursor }), replyPageSchema, signal),
    createReply: (id: string, parent_reply_id: string | null, body: string, signal: AbortSignal) =>
      request('/posts/' + encodeURIComponent(id) + '/replies', replySchema, signal, 'POST', { body, parent_reply_id }),
    updateReply: (id: string, replyId: string, body: string, signal: AbortSignal) =>
      request('/posts/' + encodeURIComponent(id) + '/replies/' + encodeURIComponent(replyId), replySchema, signal, 'PATCH', { body }),
    deleteReply: (id: string, replyId: string, signal: AbortSignal) =>
      request('/posts/' + encodeURIComponent(id) + '/replies/' + encodeURIComponent(replyId), z.undefined(), signal, 'DELETE'),
  }
}
export type CommunityApi = ReturnType<typeof createCommunityApi>
