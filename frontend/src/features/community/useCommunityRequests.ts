import { useCallback, useEffect, useRef, useState } from 'react'
import type { Page } from './communitySchemas'

export type ReadState<T> =
  | { kind: 'loading' }
  | { kind: 'error'; error: unknown }
  | { kind: 'ready'; data: T }

export function useCommunityRead<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<ReadState<T>>({ kind: 'loading' })
  const current = useRef<AbortController | null>(null)
  const reload = useCallback(() => {
    current.current?.abort()
    const request = new AbortController()
    current.current = request
    setState({ kind: 'loading' })
    void load(request.signal).then(
      data => { if (!request.signal.aborted) setState({ kind: 'ready', data }) },
      error => { if (!request.signal.aborted) setState({ kind: 'error', error }) },
    )
  }, [load])
  useEffect(() => { reload(); return () => current.current?.abort() }, [reload])
  function replace(data: T) {
    current.current?.abort()
    setState({ kind: 'ready', data })
  }
  return { state, reload, replace }
}

type Continuation = { kind: 'idle' } | { kind: 'loading' } | { kind: 'error'; error: unknown }
export type PageState<T> = ReadState<Page<T> & { continuation: Continuation }>

export function useCommunityPage<T extends { id: string }>(
  load: (cursor: string | null, signal: AbortSignal) => Promise<Page<T>>,
) {
  const [state, setState] = useState<PageState<T>>({ kind: 'loading' })
  const current = useRef<AbortController | null>(null)
  const busy = useRef(false)
  const fetchPage = useCallback((previous?: Page<T>) => {
    current.current?.abort()
    const request = new AbortController()
    current.current = request
    busy.current = true
    if (!previous) setState({ kind: 'loading' })
    else setState({ kind: 'ready', data: { ...previous, continuation: { kind: 'loading' } } })
    void load(previous?.next_cursor ?? null, request.signal).then(page => {
      if (request.signal.aborted) return
      busy.current = false
      const items = new Map((previous?.items ?? []).map(item => [item.id, item]))
      for (const item of page.items) items.set(item.id, item)
      setState({ kind: 'ready', data: { items: [...items.values()], next_cursor: page.next_cursor, continuation: { kind: 'idle' } } })
    }, error => {
      if (request.signal.aborted) return
      busy.current = false
      setState(previous
        ? { kind: 'ready', data: { ...previous, continuation: { kind: 'error', error } } }
        : { kind: 'error', error })
    })
  }, [load])
  const reload = useCallback(() => fetchPage(), [fetchPage])
  useEffect(() => { reload(); return () => current.current?.abort() }, [reload])
  function more() {
    if (!busy.current && state.kind === 'ready' && state.data.next_cursor) fetchPage(state.data)
  }
  return { state, reload, more }
}

export function useCommunityMutation() {
  const [state, setState] = useState<{ kind: 'idle' } | { kind: 'busy' } | { kind: 'error'; error: unknown }>({ kind: 'idle' })
  const current = useRef<AbortController | null>(null)
  useEffect(() => () => { current.current?.abort(); current.current = null }, [])
  async function run<T>(write: (signal: AbortSignal) => Promise<T>, success: (value: T) => void) {
    if (current.current) return
    const request = new AbortController()
    current.current = request
    setState({ kind: 'busy' })
    try {
      const value = await write(request.signal)
      if (request.signal.aborted) return
      current.current = null
      setState({ kind: 'idle' })
      success(value)
    } catch (error) {
      if (request.signal.aborted) return
      current.current = null
      setState({ kind: 'error', error })
    }
  }
  return { state, run }
}
