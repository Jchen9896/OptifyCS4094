// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AppShell from '../../src/components/layout/AppShell'
import { CommunityProvider } from '../../src/features/community/CommunityContext'
import CommunityNewPage from '../../src/features/community/CommunityNewPage'
import CommunityPostPage from '../../src/features/community/CommunityPostPage'
import { createCommunityApi } from '../../src/features/community/communityApi'

const account = vi.hoisted(() => ({ signOut: vi.fn() }))
vi.mock('@clerk/react', () => ({
  useUser: () => ({ user: null }), useClerk: () => account,
}))
vi.mock('../../src/features/portfolio/ActivePortfolioContext.tsx', () => ({
  useActivePortfolio: () => ({ activeLabel: 'Fixture portfolio' }),
}))
const post = {
  id: '11111111-1111-4111-8111-111111111111', category: 'question', title: 'Saved question', body: 'Body',
  author: { name: 'Member', picture: null }, is_mine: true, created_at: '2026-11-12T12:00:00Z', edited_at: null,
}
function show(path: string) {
  let settle: (response: Response) => void = () => {}
  const write = vi.fn(() => new Promise<Response>(resolve => { settle = resolve }))
  const api = createCommunityApi({ getToken: async () => 'fixture', fetcher: async (url, init) => {
    if (init?.method !== 'GET') return write()
    if (String(url).endsWith('/categories')) return Response.json([{ slug: 'question', label: 'Questions' }])
    if (String(url).includes('/replies')) return Response.json({ items: [], next_cursor: null })
    return Response.json(post)
  } })
  render(<MemoryRouter initialEntries={[path]}><CommunityProvider api={api} reauthenticate={() => {}}>
    <Routes><Route element={<AppShell />}>
      <Route path="/community/new" element={<CommunityNewPage />} />
      <Route path="/community/:postId" element={<CommunityPostPage />} />
      <Route path="/learn" element={<h1>Articles destination</h1>} />
    </Route></Routes>
  </CommunityProvider></MemoryRouter>)
  return { write, settle: (response: Response) => settle(response) }
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); account.signOut.mockReset() })
async function attemptLeave() {
  fireEvent.click(screen.getByRole('button', { name: 'Open navigation' }))
  fireEvent.click(screen.getByRole('link', { name: 'Articles' }))
  expect(screen.queryByRole('heading', { name: 'Articles destination' })).toBeNull()
  expect(screen.getByRole('dialog')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
  expect(account.signOut).not.toHaveBeenCalled()
  expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('may still complete'))
  fireEvent.click(screen.getByRole('button', { name: 'Close menu' }))
}
describe('dispatched Community writes', () => {
  it('keeps a new post mounted across attempted navigation and sign-out until success', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.spyOn(window, 'alert').mockImplementation(() => {})
    const pending = show('/community/new')
    await screen.findByLabelText('Title')
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Keep title' } })
    fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'question' } })
    fireEvent.change(screen.getByLabelText('Post'), { target: { value: 'Keep body' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save post' }))
    await waitFor(() => expect(pending.write).toHaveBeenCalledOnce())
    await attemptLeave()
    expect(window.confirm).not.toHaveBeenCalled()
    expect(screen.getByLabelText<HTMLInputElement>('Title').value).toBe('Keep title')
    fireEvent.submit(screen.getByRole('button', { name: 'Saving…' }).closest('form')!)
    expect(pending.write).toHaveBeenCalledOnce()
    await act(async () => pending.settle(Response.json(post)))
    await screen.findByRole('heading', { name: 'Saved question' })
    fireEvent.click(screen.getByRole('button', { name: 'Open navigation' }))
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(account.signOut).toHaveBeenCalledOnce()
  })
  it('guards a delete without a dirty draft, warns on unload, and releases after failure', async () => {
    vi.spyOn(window, 'alert').mockImplementation(() => {})
    const pending = show('/community/' + post.id)
    await screen.findByLabelText('Your reply')
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete post' }))
    await waitFor(() => expect(pending.write).toHaveBeenCalledOnce())
    const unload = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(unload)
    expect(unload.defaultPrevented).toBe(true)
    // The delete dialog already owns the modal. Its backdrop cannot bypass link capture.
    fireEvent.click(screen.getByRole('link', { name: 'Articles', hidden: true }))
    expect(screen.queryByRole('heading', { name: 'Articles destination' })).toBeNull()
    fireEvent.keyDown(document.activeElement!, { key: 'Escape' })
    expect(screen.getByRole('dialog')).toBeTruthy()
    await act(async () => pending.settle(new Response(null, { status: 503 })))
    await screen.findByRole('alert')
    expect(screen.getByRole('alert').textContent).toContain('may have completed')
    const settledUnload = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(settledUnload)
    expect(settledUnload.defaultPrevented).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    fireEvent.click(screen.getByRole('button', { name: 'Open navigation' }))
    fireEvent.click(screen.getByRole('link', { name: 'Articles' }))
    await screen.findByRole('heading', { name: 'Articles destination' })
  })
})
