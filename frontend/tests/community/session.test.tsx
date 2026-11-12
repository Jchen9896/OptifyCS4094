// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CommunitySession from '../../src/features/community/CommunitySession'
import CommunityNewPage from '../../src/features/community/CommunityNewPage'

const session = vi.hoisted(() => ({ userId: 'first', sessionId: 'session-one' }))
vi.mock('@clerk/react', () => ({
  useAuth: () => ({ ...session, getToken: async () => session.userId }),
  useClerk: () => ({ signOut: async () => {} }),
}))
beforeEach(() => { session.userId = 'first'; session.sessionId = 'session-one' })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
function App() {
  return <MemoryRouter><Routes><Route element={<CommunitySession />}>
    <Route path="/" element={<CommunityNewPage />} />
  </Route></Routes></MemoryRouter>
}
describe('real session boundary with injected Clerk values', () => {
  it('drops an old dispatched write on a forced account switch without touching the new draft', async () => {
    let finishWrite: (response: Response) => void = () => {}
    let writes = 0
    vi.stubGlobal('fetch', vi.fn((_url, init: RequestInit) => {
      if (init.method === 'POST') {
        writes++
        return new Promise<Response>(resolve => { finishWrite = resolve })
      }
      return Promise.resolve(Response.json([{ slug: 'question', label: 'Questions' }]))
    }))
    const view = render(<App />)
    await screen.findByLabelText('Title')
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Old account title' } })
    fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'question' } })
    fireEvent.change(screen.getByLabelText('Post'), { target: { value: 'Old account body' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save post' }))
    await waitFor(() => expect(writes).toBe(1))
    session.userId = 'second'
    session.sessionId = 'session-two'
    view.rerender(<App />)
    await waitFor(() => expect(screen.getByLabelText<HTMLInputElement>('Title').value).toBe(''))
    const unload = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(unload)
    expect(unload.defaultPrevented).toBe(false)
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'New account draft' } })
    await act(async () => finishWrite(Response.json({
      id: '11111111-1111-4111-8111-111111111111', category: 'question', title: 'Old account title', body: 'Old account body',
      author: { name: 'Old member', picture: null }, is_mine: true, created_at: '2026-11-12T12:00:00Z', edited_at: null,
    })))
    expect(screen.getByLabelText<HTMLInputElement>('Title').value).toBe('New account draft')
    expect(screen.queryByText('Old account body')).toBeNull()
    expect(screen.queryByRole('alert')).toBeNull()
    expect(writes).toBe(1)
  })
  it('ignores late categories from the old account and clears drafts on a new session', async () => {
    let finishOld: (response: Response) => void = () => {}
    vi.stubGlobal('fetch', vi.fn((_url, init: RequestInit) => {
      const headers = new Headers(init.headers)
      return headers.get('Authorization') === 'Bearer first'
        ? new Promise<Response>(resolve => { finishOld = resolve })
        : Promise.resolve(Response.json([{ slug: 'question', label: 'Current account questions' }]))
    }))
    const view = render(<App />)
    await waitFor(() => expect(fetch).toHaveBeenCalledOnce())
    session.userId = 'second'
    session.sessionId = 'session-two'
    view.rerender(<App />)
    await screen.findByLabelText('Title')
    expect(screen.getByRole('option', { name: 'Current account questions' })).toBeTruthy()
    await act(async () => finishOld(Response.json([{ slug: 'discussion', label: 'Old account category' }])))
    await waitFor(() => expect(screen.queryByRole('option', { name: 'Old account category' })).toBeNull())
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Account-local draft' } })
    session.sessionId = 'session-three'
    view.rerender(<App />)
    await waitFor(() => expect(screen.getByLabelText<HTMLInputElement>('Title').value).toBe(''))
    expect(screen.getByRole('option', { name: 'Current account questions' })).toBeTruthy()
  })
})
