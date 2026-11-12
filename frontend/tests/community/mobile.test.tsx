// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CommunityMobileMenu } from '../../src/features/community/CommunityMobileMenu'
import { ReplyEditor } from '../../src/features/community/CommunityEditor'
import { requestCommunityLeave } from '../../src/features/community/communityDrafts'

afterEach(() => { cleanup(); vi.restoreAllMocks() })
function CurrentRoute() { return <p>{useLocation().pathname}</p> }
function ScopedMenu() {
  const location = useLocation()
  return <>{location.pathname.startsWith('/community') && <CommunityMobileMenu email="fixture@example.test" activeLabel="New portfolio" signOut={() => {}} />}<main><h1>Destination</h1></main></>
}
describe('mobile navigation and explicit draft disposal', () => {
  it('retains all navigation actions and closes with focus restored on navigation', async () => {
    render(<MemoryRouter initialEntries={['/community']}><CommunityMobileMenu email="fixture@example.test" activeLabel="New portfolio" signOut={() => {}} /><CurrentRoute /></MemoryRouter>)
    const trigger = screen.getByRole('button', { name: 'Open navigation' })
    fireEvent.click(trigger)
    expect(screen.getByRole('link', { name: 'Portfolio manager' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeTruthy()
    fireEvent.click(screen.getByRole('link', { name: 'Articles' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    await waitFor(() => expect(document.activeElement).toBe(trigger))
    expect(screen.getByText('/learn')).toBeTruthy()
  })
  it('focuses the destination when navigation removes the Community-only trigger', async () => {
    render(<MemoryRouter initialEntries={['/community']}><ScopedMenu /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'Open navigation' }))
    fireEvent.click(screen.getByRole('link', { name: 'Articles' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'Destination' })))
  })
  it('blocks explicit leave controls while keeping the unsaved draft', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<ReplyEditor busy={false} onSubmit={() => {}} />)
    fireEvent.change(screen.getByLabelText('Your reply'), { target: { value: 'Keep me' } })
    expect(requestCommunityLeave()).toBe(false)
    expect(screen.getByLabelText<HTMLTextAreaElement>('Your reply').value).toBe('Keep me')
  })
})
