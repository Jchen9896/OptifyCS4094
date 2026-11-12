import { z } from 'zod'
import { createCommunityApi } from '../../src/features/community/communityApi'
import type { Post, Reply } from '../../src/features/community/communitySchemas'

const date = '2026-11-12T12:00:00Z'
const author = { name: 'Alex Morgan', picture: 'https://invalid.example.test/avatar.png' }
const postId = '11111111-1111-4111-8111-111111111111'
const replyId = '22222222-2222-4222-8222-222222222222'
const seed = {
  id: postId, category: 'discussion', title: 'How do you keep a portfolio balanced?', is_mine: true,
  body: 'I am reviewing my allocation for the year. **How often do you rebalance?**\n\n- Set a schedule\n- Watch allocation drift\n\n> Share what works for you. This is a discussion, not financial advice.\n\n[Read the guide](https://example.test/' + 'long-link-'.repeat(30) + ')\n\n~~~text\n' + 'long_code_without_wrapping_'.repeat(20) + '\n~~~',
  author, created_at: date, edited_at: null,
} satisfies Post
const posts: Post[] = [seed,
  { ...seed, id: '44444444-4444-4444-8444-444444444444', category: 'question', title: 'Understanding diversification', is_mine: false, body: 'What should a beginner know about diversification?', author: { name: 'Member', picture: null } },
  { ...seed, id: '55555555-5555-4555-8555-555555555555', category: 'portfolio', title: 'A long-term investing approach', body: 'I focus on broad diversification and regular contributions.' },
]
const replies: Reply[] = [
  { id: replyId, post_id: postId, parent_reply_id: null, body: 'I review quarterly and rebalance when allocations drift.', created_at: date, edited_at: null, deleted_at: null, author, is_mine: true },
  { id: '33333333-3333-4333-8333-333333333333', post_id: postId, parent_reply_id: replyId, body: 'Do you use a fixed percentage threshold?', created_at: date, edited_at: null, deleted_at: null, author: { name: 'Jamie', picture: null }, is_mine: false },
  { id: '66666666-6666-4666-8666-666666666666', post_id: postId, parent_reply_id: null, body: null, created_at: date, edited_at: null, deleted_at: date, author: null, is_mine: false },
  { id: '77777777-7777-4777-8777-777777777777', post_id: postId, parent_reply_id: '66666666-6666-4666-8666-666666666666', body: 'This response survives a deleted parent.', created_at: date, edited_at: null, deleted_at: null, author, is_mine: false },
]
export const fixtureFailures = { read: false, write: false }
const input = z.object({ title: z.string(), body: z.string(), category: z.string() })
const replyInput = z.object({ body: z.string(), parent_reply_id: z.string().nullable().optional() })
export const fixtureApi = createCommunityApi({
  getToken: async () => 'fixture-only-not-a-Clerk-token',
  fetcher: async (raw, init) => {
    const url = new URL(String(raw), 'http://fixture.test')
    const parts = url.pathname.split('/').filter(Boolean).slice(2)
    const method = init?.method ?? 'GET'
    const failure = method === 'GET' ? 'read' : 'write'
    if (fixtureFailures[failure]) {
      fixtureFailures[failure] = false
      return Response.json({ detail: { code: 'unavailable' } }, { status: 503 })
    }
    if (parts[0] === 'categories') return Response.json([
      { slug: 'question', label: 'Questions' }, { slug: 'discussion', label: 'Discussions' }, { slug: 'portfolio', label: 'Portfolios' },
    ])
    const id = parts[1]
    const post = posts.find(row => row.id === id)
    const data: unknown = init?.body ? JSON.parse(String(init.body)) : undefined
    if (parts[2] === 'replies') {
      const reply = replies.find(row => row.id === parts[3])
      if (method === 'DELETE' && reply) {
        replies.splice(replies.indexOf(reply), 1, { ...reply, body: null, author: null, deleted_at: new Date().toISOString() })
        return new Response(null, { status: 204 })
      }
      if (method === 'PATCH' && reply && reply.deleted_at === null) {
        const saved = { ...reply, body: replyInput.parse(data).body, edited_at: new Date().toISOString() }
        replies.splice(replies.indexOf(reply), 1, saved)
        return Response.json(saved)
      }
      if (method === 'POST') {
        const value = replyInput.parse(data)
        const saved = { ...replies[0], id: crypto.randomUUID(), post_id: id, parent_reply_id: value.parent_reply_id ?? null, body: value.body, created_at: new Date().toISOString(), deleted_at: null, author, is_mine: true }
        replies.push(saved)
        return Response.json(saved, { status: 201 })
      }
      const rows = replies.filter(row => row.post_id === id && row.parent_reply_id === url.searchParams.get('parent_reply_id'))
      return Response.json({ items: rows, next_cursor: null })
    }
    if (method === 'POST') {
      const saved = { ...seed, ...input.parse(data), id: crypto.randomUUID(), created_at: new Date().toISOString() }
      posts.unshift(saved)
      return Response.json(saved, { status: 201 })
    }
    if (method === 'PATCH' && post) { Object.assign(post, input.parse(data), { edited_at: new Date().toISOString() }); return Response.json(post) }
    if (method === 'DELETE' && post) { posts.splice(posts.indexOf(post), 1); return new Response(null, { status: 204 }) }
    if (id) return post ? Response.json(post) : new Response(null, { status: 404 })
    const rows = posts.filter(row => !url.searchParams.get('category') || row.category === url.searchParams.get('category'))
    const start = url.searchParams.has('cursor') ? 2 : 0
    return Response.json({ items: rows.slice(start, start + 2), next_cursor: start + 2 < rows.length ? 'fixture-next' : null })
  },
})
