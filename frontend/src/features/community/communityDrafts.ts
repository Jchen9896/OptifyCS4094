import { useEffect } from 'react'

const discardEvent = 'community-discard-draft'
const pendingEvent = 'community-pending-write'

export function requestCommunityLeave(): boolean {
  return window.dispatchEvent(new Event(pendingEvent, { cancelable: true })) &&
    window.dispatchEvent(new Event(discardEvent, { cancelable: true }))
}

export function beginCommunityWrite(): (() => void) | null {
  if (!window.dispatchEvent(new Event(pendingEvent, { cancelable: true }))) return null
  const block = (event: Event) => {
    event.preventDefault()
    event.stopImmediatePropagation()
    window.alert('A Community write is pending. Wait for the result before leaving or signing out. If you close this page, the write may still complete. Check the discussion before submitting again.')
  }
  const navigate = (event: MouseEvent) => {
    if (event.target instanceof Element && event.target.closest('a[href]')) block(event)
  }
  const unload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
  window.addEventListener(pendingEvent, block)
  window.addEventListener('beforeunload', unload)
  window.addEventListener('click', navigate, true)
  return () => {
    window.removeEventListener(pendingEvent, block)
    window.removeEventListener('beforeunload', unload)
    window.removeEventListener('click', navigate, true)
  }
}

export function useDraftWarning(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return
    const unload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    const discard = (event: Event) => {
      if (!window.confirm('Discard your unsaved draft?')) {
        event.preventDefault()
        event.stopImmediatePropagation()
      }
    }
    const navigate = (event: MouseEvent) => {
      if (event.target instanceof Element && event.target.closest('a[href]')) discard(event)
    }
    window.addEventListener('beforeunload', unload)
    window.addEventListener(discardEvent, discard)
    document.addEventListener('click', navigate, true)
    return () => {
      window.removeEventListener('beforeunload', unload)
      window.removeEventListener(discardEvent, discard)
      document.removeEventListener('click', navigate, true)
    }
  }, [dirty])
}
