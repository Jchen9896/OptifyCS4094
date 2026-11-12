import { useEffect } from 'react'

const discardEvent = 'community-discard-draft'

export function requestCommunityLeave(): boolean {
  return window.dispatchEvent(new Event(discardEvent, { cancelable: true }))
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
