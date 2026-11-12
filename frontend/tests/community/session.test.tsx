// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CommunitySession from '../../src/features/community/CommunitySession'
import CommunityNewPage from '../../src/features/community/CommunityNewPage'

const session = vi.hoisted(() => ({ userId: 'first', sessionId: 'session-one' }))
vi.mock('@clerk/react', () => ({
  useAuth: () => ({ ...session, getToken: async () => session.userId }),
  useClerk: () => ({ signOut: async () => {} }),
}))
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
function App() {
  return <MemoryRouter><Routes><Route element={<CommunitySession />}>
    <Route path="/" element={<CommunityNewPage />} />
  </Route></Routes></MemoryRouter>
}
describe('real session boundary with injected Clerk values', () => {
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
