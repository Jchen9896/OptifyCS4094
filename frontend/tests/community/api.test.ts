import { describe, it, expect } from 'vitest'
import { createCommunityApi, CommunityError, errorMessage } from '../../src/features/community/communityApi'
import { replySchema } from '../../src/features/community/communitySchemas'

export const post = {
  id: '11111111-1111-4111-8111-111111111111', category: 'question', title: 'A question', body: 'Hello',
  author: { name: 'Member', picture: null }, is_mine: true,
  created_at: '2026-11-12T12:00:00Z', edited_at: null,
}
const signal = () => new AbortController().signal

describe('Community boundary', () => {
  it('gets a fresh bearer for every request and sends only content', async () => {
    let token = 0
    const requests: RequestInit[] = []
    const api = createCommunityApi({
      getToken: async () => 'token' + ++token,
      fetcher: async (_url, init) => { requests.push(init!); return Response.json(post) },
    })
    await api.createPost({ title: post.title, body: post.body, category: post.category }, signal())
    await api.updatePost(post.id, post, signal())
    expect(requests.map(r => r.headers)).toEqual([
      { Authorization: 'Bearer token1', 'Content-Type': 'application/json' }, { Authorization: 'Bearer token2', 'Content-Type': 'application/json' },
    ])
    expect(requests.map(request => JSON.parse(String(request.body)))).toEqual([
      { title: post.title, body: post.body, category: post.category },
      { title: post.title, body: post.body, category: post.category },
    ])
  })
  it('accepts empty deletes and rejects malformed success responses', async () => {
    const api = createCommunityApi({ getToken: async () => 'token', fetcher: async () => new Response(null, { status: 204 }) })
    await expect(api.deletePost(post.id, signal())).resolves.toBeUndefined()
    await expect(api.post(post.id, signal())).rejects.toMatchObject({ kind: 'invalid' })
  })
  it('parses live anonymous replies and rejects partial tombstones', () => {
    const reply = { ...post, post_id: post.id, parent_reply_id: null, deleted_at: null }
    expect(replySchema.parse(reply).body).toBe('Hello')
    expect(replySchema.safeParse({ ...reply, body: null }).success).toBe(false)
    expect(replySchema.parse({ ...reply, body: null, author: null, deleted_at: post.created_at }).body).toBeNull()
    expect(replySchema.safeParse({ ...reply, created_at: 'yesterday' }).success).toBe(false)
  })
  it.each([[401, 'session'], [404, 'missing'], [422, 'validation'], [503, 'unavailable']])('classifies HTTP %s', async (status, kind) => {
    const api = createCommunityApi({ getToken: async () => 'token', fetcher: async () => new Response(null, { status: Number(status) }) })
    await expect(api.post(post.id, signal())).rejects.toMatchObject({ kind })
  })
  it('recognizes the backend invalid-cursor detail envelope', async () => {
    const api = createCommunityApi({ getToken: async () => 'token', fetcher: async () => Response.json({ detail: { code: 'invalid_cursor', message: 'Invalid' } }, { status: 422 }) })
    await expect(api.posts('', 'old', signal())).rejects.toMatchObject({ kind: 'cursor' })
  })
  it('stops writes after expiry without retrying', async () => {
    let requests = 0
    const api = createCommunityApi({ getToken: async () => 'token', fetcher: async () => { requests++; return new Response(null, { status: 401 }) } })
    await expect(api.post(post.id, signal())).rejects.toBeInstanceOf(CommunityError)
    await expect(api.createPost(post, signal())).rejects.toMatchObject({ kind: 'session' })
    expect(requests).toBe(1)
  })
  it('stops a waiting-token write when another request expires the session', async () => {
    let finish: (token: string) => void = () => {}
    let tokens = 0
    let requests = 0
    const api = createCommunityApi({
      getToken: () => ++tokens === 1 ? new Promise(resolve => { finish = resolve }) : Promise.resolve('expired'),
      fetcher: async () => { requests++; return new Response(null, { status: 401 }) },
    })
    const write = api.createPost(post, signal())
    await expect(api.post(post.id, signal())).rejects.toMatchObject({ kind: 'session' })
    finish('old-token')
    await expect(write).rejects.toMatchObject({ kind: 'session' })
    expect(requests).toBe(1)
  })
  it('marks an already-sent write uncertain if another request expires its session', async () => {
    let finish: (response: Response) => void = () => {}
    const api = createCommunityApi({
      getToken: async () => 'token',
      fetcher: async (_url, init) => init?.method === 'POST'
        ? new Promise(resolve => { finish = resolve })
        : new Response(null, { status: 401 }),
    })
    const write = api.createPost(post, signal())
    await Promise.resolve()
    await expect(api.post(post.id, signal())).rejects.toMatchObject({ kind: 'session' })
    finish(Response.json(post))
    const error = await write.catch(error => error)
    expect(error).toMatchObject({ kind: 'session', uncertain: true })
    expect(errorMessage(error, true)).toContain('may have completed')
  })
  it('rejects completions from a disposed account even when fetch ignores abort', async () => {
    let finish: (r: Response) => void = () => {}
    const api = createCommunityApi({ getToken: async () => 'token', fetcher: () => new Promise(resolve => { finish = resolve }) })
    const result = api.post(post.id, signal())
    await Promise.resolve()
    api.dispose()
    finish(Response.json(post))
    await expect(result).rejects.toMatchObject({ name: 'AbortError' })
  })
})
