// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useCommunityPage, useCommunityRead, useCommunityMutation } from '../../src/features/community/useCommunityRequests'

function deferred<T>() {
  let resolve: (value: T) => void = () => {}
  let reject: (error: Error) => void = () => {}
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
describe('request ownership', () => {
  it('does not restore an older read over an authoritative mutation', async () => {
    const pending = deferred<string>()
    const load = () => pending.promise
    const { result } = renderHook(() => useCommunityRead(load))
    act(() => result.current.replace('edited'))
    await act(async () => pending.resolve('old'))
    expect(result.current.state).toEqual({ kind: 'ready', data: 'edited' })
  })
  it('resets pagination on category scope changes and ignores old reads', async () => {
    const pending = deferred<{ items: { id: string }[]; next_cursor: null }>()
    const first = () => pending.promise
    const second = async () => ({ items: [{ id: 'new' }], next_cursor: null })
    const { result, rerender } = renderHook(({ load }) => useCommunityPage(load), { initialProps: { load: first } })
    rerender({ load: second })
    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
    await act(async () => pending.resolve({ items: [{ id: 'old' }], next_cursor: null }))
    expect(result.current.state).toMatchObject({ data: { items: [{ id: 'new' }], next_cursor: null } })
  })
  it('keeps rows and cursor on continuation errors and deduplicates retry results', async () => {
    let attempt = 0
    const load = async (cursor: string | null) => {
      if (!cursor) return { items: [{ id: 'one' }], next_cursor: 'next' }
      if (++attempt === 1) throw Error('offline')
      return { items: [{ id: 'one' }, { id: 'two' }], next_cursor: null }
    }
    const { result } = renderHook(() => useCommunityPage(load))
    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
    act(() => result.current.more())
    await waitFor(() => expect(result.current.state).toMatchObject({ data: { next_cursor: 'next', continuation: { kind: 'error' } } }))
    act(() => result.current.more())
    await waitFor(() => expect(result.current.state).toMatchObject({ data: { items: [{ id: 'one' }, { id: 'two' }], next_cursor: null } }))
  })
  it('does not resurrect an older sibling read over a successful mutation', async () => {
    const pending = deferred<{ items: { id: string; text: string }[]; next_cursor: null }>()
    const load = (cursor: string | null) => cursor ? pending.promise : Promise.resolve({ items: [{ id: 'one', text: 'old' }], next_cursor: 'next' })
    const { result } = renderHook(() => useCommunityPage(load))
    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
    act(() => result.current.more())
    act(() => result.current.invalidate({ id: 'one', text: 'edited' }))
    await act(async () => pending.resolve({ items: [{ id: 'one', text: 'old' }], next_cursor: null }))
    expect(result.current.state).toMatchObject({ data: { items: [{ id: 'one', text: 'edited' }], next_cursor: 'next', continuation: { kind: 'idle' } } })
  })
  it('prevents duplicate writes even before a busy render', async () => {
    const pending = deferred<string>()
    let writes = 0
    let completions = 0
    const { result } = renderHook(useCommunityMutation)
    const write = () => { writes++; return pending.promise }
    act(() => {
      void result.current.run(write, () => { completions++ })
      void result.current.run(write, () => { completions++ })
    })
    expect(writes).toBe(1)
    await act(async () => pending.resolve('saved'))
    expect(completions).toBe(1)
  })
  it('never runs an old account mutation callback after unmount', async () => {
    const pending = deferred<string>()
    let completed = false
    const { result, unmount } = renderHook(useCommunityMutation)
    let running: Promise<void>
    act(() => { running = result.current.run(() => pending.promise, () => { completed = true }) })
    unmount()
    pending.resolve('saved')
    await act(async () => running)
    expect(completed).toBe(false)
  })
})
