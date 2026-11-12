// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { CommunityProvider } from '../../src/features/community/CommunityContext'
import { createCommunityApi } from '../../src/features/community/communityApi'
import CommunityFeedPage from '../../src/features/community/CommunityFeedPage'
import CommunityNewPage from '../../src/features/community/CommunityNewPage'

const post = {
  id: '11111111-1111-4111-8111-111111111111', category: 'question', title: 'A question', body: 'Hello **world**',
  author: { name: 'Member', picture: null }, is_mine: true, created_at: '2026-11-12T12:00:00Z', edited_at: null,
}
afterEach(cleanup)
describe('feed and creation', () => {
  it('uses server category labels and resets the list when a filter changes', async () => {
    const urls: string[] = []
    const api = createCommunityApi({ getToken: async () => 'fixture', fetcher: async url => {
      urls.push(String(url))
      return Response.json(String(url).endsWith('/categories') ? [{ slug: 'question', label: 'Questions' }] : {
        items: String(url).includes('category=question') ? [] : [post], next_cursor: null,
      })
    } })
    render(<MemoryRouter><CommunityProvider api={api} reauthenticate={() => {}}><CommunityFeedPage /></CommunityProvider></MemoryRouter>)
    await screen.findByRole('link', { name: 'A question' })
    expect(screen.getByText('world').tagName).toBe('STRONG')
    fireEvent.click(screen.getByRole('button', { name: 'Questions' }))
    await screen.findByRole('heading', { name: 'Start a conversation' })
    expect(screen.queryByRole('link', { name: 'A question' })).toBeNull()
    expect(urls.at(-1)).toBe('/api/community/posts?category=question')
  })
  it('retains all fields after a failed create and navigates only on success', async () => {
    let attempts = 0
    const api = createCommunityApi({ getToken: async () => 'fixture', fetcher: async (url, init) => {
      if (String(url).endsWith('/categories')) return Response.json([{ slug: 'question', label: 'Questions' }])
      if (init?.method === 'POST' && ++attempts === 1) return new Response(null, { status: 503 })
      return Response.json(post)
    } })
    render(<MemoryRouter initialEntries={['/community/new']}><CommunityProvider api={api} reauthenticate={() => {}}>
      <Routes><Route path="/community/new" element={<CommunityNewPage />} /><Route path="/community/:id" element={<p>Created discussion</p>} /></Routes>
    </CommunityProvider></MemoryRouter>)
    await screen.findByLabelText('Title')
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'A question' } })
    fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'question' } })
    fireEvent.change(screen.getByLabelText('Post'), { target: { value: 'Draft body' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save post' }))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('draft is kept'))
    expect(screen.getByLabelText<HTMLTextAreaElement>('Post').value).toBe('Draft body')
    fireEvent.click(screen.getByRole('button', { name: 'Save post' }))
    await screen.findByText('Created discussion')
  })
})
