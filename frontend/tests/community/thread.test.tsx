// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { CommunityProvider } from '../../src/features/community/CommunityContext'
import { createCommunityApi } from '../../src/features/community/communityApi'
import CommunityPostPage from '../../src/features/community/CommunityPostPage'

const post = {
  id: '11111111-1111-4111-8111-111111111111', category: 'question', title: 'A question', body: 'Hello',
  author: { name: 'Member', picture: null }, is_mine: true, created_at: '2026-11-12T12:00:00Z', edited_at: null,
}
const reply = { ...post, id: '22222222-2222-4222-8222-222222222222', post_id: post.id, parent_reply_id: null, body: 'Parent text', deleted_at: null }
const child = { ...reply, id: '33333333-3333-4333-8333-333333333333', parent_reply_id: reply.id, body: 'Child text', is_mine: false }
function show(fetcher: typeof fetch) {
  const api = createCommunityApi({ getToken: async () => 'fixture', fetcher })
  return render(<MemoryRouter initialEntries={['/community/' + post.id]}><CommunityProvider api={api} reauthenticate={() => {}}>
    <Routes><Route path="/community/:postId" element={<CommunityPostPage />} /></Routes>
  </CommunityProvider></MemoryRouter>)
}
afterEach(cleanup)
describe('discussion ownership and lazy siblings', () => {
  it('loads only expanded branches and retains descendants after deletion', async () => {
    const urls: string[] = []
    show(async (url, init) => {
      urls.push(String(url))
      if (init?.method === 'DELETE') return new Response(null, { status: 204 })
      if (String(url).endsWith('/categories')) return Response.json([{ slug: 'question', label: 'Questions' }])
      if (String(url).includes('/replies')) return Response.json({ items: String(url).includes('parent_reply_id') ? [child] : [reply], next_cursor: null })
      return Response.json(post)
    })
    const parent = (await screen.findByText('Parent text')).closest('li')!
    expect(urls.filter(url => url.includes('parent_reply_id'))).toHaveLength(0)
    fireEvent.click(within(parent).getByRole('button', { name: 'Show replies' }))
    await screen.findByText('Child text')
    expect(urls.filter(url => url.includes('parent_reply_id'))).toHaveLength(1)
    const childRow = screen.getByText('Child text').closest('li')!
    expect(within(childRow).queryByRole('button', { name: 'Edit' })).toBeNull()
    fireEvent.click(within(parent).getByRole('button', { name: 'Delete' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete reply' }))
    await screen.findByText('This reply was deleted.')
    expect(screen.queryByText('Parent text')).toBeNull()
    expect(screen.getByText('Child text')).toBeTruthy()
    expect(within(parent).queryByRole('button', { name: 'Delete' })).toBeNull()
    await waitFor(() => expect(document.activeElement).toBe(within(parent).getAllByRole('button', { name: 'Reply' })[0]))
  })
  it('renders authoritative tombstones without text, author or owner actions', async () => {
    show(async url => {
      if (String(url).endsWith('/categories')) return Response.json([])
      if (String(url).includes('/replies')) return Response.json({ items: [{ ...reply, body: null, author: null, deleted_at: post.created_at }], next_cursor: null })
      return Response.json({ ...post, is_mine: false })
    })
    const row = (await screen.findByText('This reply was deleted.')).closest('li')!
    expect(within(row).queryByText('Member')).toBeNull()
    expect(within(row).queryByRole('button', { name: 'Delete' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Edit post' })).toBeNull()
    expect(within(row).getByRole('button', { name: 'Show replies' })).toBeTruthy()
  })
  it('edits an owned post using the authoritative response without clearing sibling drafts', async () => {
    show(async (url, init) => {
      if (String(url).endsWith('/categories')) return Response.json([{ slug: 'question', label: 'Questions' }])
      if (String(url).includes('/replies')) return Response.json({ items: [], next_cursor: null })
      if (init?.method === 'PATCH') return Response.json({ ...post, title: 'Edited title', edited_at: post.created_at })
      return Response.json(post)
    })
    await screen.findByLabelText('Your reply')
    fireEvent.change(screen.getByLabelText('Your reply'), { target: { value: 'Keep this draft' } })
    fireEvent.click(screen.getByRole('button', { name: 'Edit post' }))
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Edited title' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save post' }))
    await screen.findByRole('heading', { name: 'Edited title' })
    await waitFor(() => expect(screen.queryByLabelText('Title')).toBeNull())
    expect(screen.getByLabelText<HTMLTextAreaElement>('Your reply').value).toBe('Keep this draft')
  })
})
