// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CommunityProvider } from '../../src/features/community/CommunityContext'
import { DeleteCommunityItem, CommunityFailure } from '../../src/features/community/CommunityShared'
import { createCommunityApi, CommunityError } from '../../src/features/community/communityApi'

const api = createCommunityApi({ getToken: async () => 'fixture', fetcher: async () => Response.json([]) })
afterEach(cleanup)
describe('Community confirmations', () => {
  it('focuses Cancel, restores trigger focus on Escape, and does not delete', async () => {
    const remove = vi.fn(async () => {})
    render(<CommunityProvider api={api} reauthenticate={() => {}}><DeleteCommunityItem kind="post" remove={remove} onDeleted={() => {}} /></CommunityProvider>)
    const trigger = screen.getByRole('button', { name: 'Delete' })
    fireEvent.click(trigger)
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Cancel' })))
    expect(screen.getByText('This permanently removes the post and its entire discussion.')).toBeTruthy()
    fireEvent.keyDown(document.activeElement!, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    await waitFor(() => expect(document.activeElement).toBe(trigger))
    expect(remove).not.toHaveBeenCalled()
  })
  it('keeps failed delete confirmation open with an uncertain-write warning', async () => {
    render(<CommunityProvider api={api} reauthenticate={() => {}}><DeleteCommunityItem kind="reply" remove={async () => { throw Error('offline') }} onDeleted={() => {}} /></CommunityProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete reply' }))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('may have completed'))
    expect(screen.getByRole('dialog')).toBeTruthy()
  })
  it('offers explicit reauthentication rather than retrying an expired session', () => {
    const reauthenticate = vi.fn()
    render(<CommunityProvider api={api} reauthenticate={reauthenticate}><CommunityFailure error={new CommunityError('session', 'Expired')} retry={() => {}} /></CommunityProvider>)
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Sign in again' }))
    expect(reauthenticate).toHaveBeenCalledOnce()
  })
})
