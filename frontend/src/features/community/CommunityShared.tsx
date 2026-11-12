import { useRef, useState } from 'react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { CommunityError, errorMessage } from './communityApi'
import { useCommunity } from './CommunityContext'
import { requestCommunityLeave } from './communityDrafts'
import { useCommunityMutation } from './useCommunityRequests'
import type { Author } from './communitySchemas'
import type { PageState } from './useCommunityRequests'

export function CommunityAuthor({ author, createdAt, editedAt }: { author: Author; createdAt: string; editedAt: string | null }) {
  const name = author.name.trim() || 'Member'
  return <div className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted-foreground">
    <Avatar size="sm">
      {author.picture && <AvatarImage src={author.picture} alt="" referrerPolicy="no-referrer" />}
      <AvatarFallback>{name.slice(0, 2).toUpperCase()}</AvatarFallback>
    </Avatar>
    <span className="break-all font-medium text-foreground">{name}</span>
    <time dateTime={createdAt} title={new Date(createdAt).toLocaleString()}>{new Date(createdAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</time>
    {editedAt && <span title={new Date(editedAt).toLocaleString()}>Edited</span>}
  </div>
}

export function CommunityWritePending() {
  return <p role="status" className="text-sm text-muted-foreground">A Community write is pending. Wait for the result before leaving. Closing this page does not undo the write. If interrupted, check the discussion before submitting again.</p>
}

export function CommunityFailure({ error, retry, write = false }: { error: unknown; retry?: () => void; write?: boolean }) {
  const { reauthenticate } = useCommunity()
  const expired = error instanceof CommunityError && error.kind === 'session'
  return <Alert variant="destructive" role="alert">
    <AlertDescription className="space-y-2">
      <p>{errorMessage(error, write)}</p>
      {expired ? <Button variant="outline" size="sm" onClick={reauthenticate}>Sign in again</Button>
        : retry && <Button variant="outline" size="sm" onClick={retry}>{error instanceof CommunityError && error.kind === 'cursor' ? 'Reload list' : 'Try again'}</Button>}
    </AlertDescription>
  </Alert>
}

export function PageContinuation<T>({ state, more, reload }: { state: PageState<T>; more: () => void; reload: () => void }) {
  if (state.kind === 'loading') return <p role="status" className="text-sm text-muted-foreground">Loading…</p>
  if (state.kind === 'error') return <CommunityFailure error={state.error} retry={reload} />
  const continuation = state.data.continuation
  return <div className="space-y-3">
    {continuation.kind === 'error' && <CommunityFailure error={continuation.error} retry={
      continuation.error instanceof CommunityError && continuation.error.kind === 'cursor'
        ? () => { if (requestCommunityLeave()) reload() } : more
    } />}
    {state.data.next_cursor && <Button variant="outline" disabled={continuation.kind === 'loading'} onClick={more}>
      {continuation.kind === 'loading' ? 'Loading…' : 'Load more'}
    </Button>}
  </div>
}

export function DeleteCommunityItem({ kind, remove, onDeleted, restoreFocus }: {
  kind: 'post' | 'reply'; remove: (signal: AbortSignal) => Promise<void>; onDeleted: () => void; restoreFocus?: () => void
}) {
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  const cancel = useRef<HTMLButtonElement>(null)
  const mutation = useCommunityMutation()
  const busy = mutation.state.kind === 'busy'
  return <>
    <Button ref={trigger} size="sm" variant="ghost" onClick={() => setOpen(true)}>Delete</Button>
    <Dialog open={open} onOpenChange={next => { if (!busy) setOpen(next) }}>
      <DialogContent onOpenAutoFocus={event => { event.preventDefault(); cancel.current?.focus() }}
        onCloseAutoFocus={event => {
          event.preventDefault()
          if (trigger.current?.isConnected) trigger.current.focus()
          else restoreFocus?.()
        }}>
        <DialogTitle>Delete {kind}?</DialogTitle>
        <DialogDescription>{kind === 'post' ? 'This permanently removes the post and its entire discussion.' : 'Your reply becomes a deleted placeholder. Replies to it remain available.'}</DialogDescription>
        {mutation.state.kind === 'error' && <CommunityFailure error={mutation.state.error} write />}
        {busy && <CommunityWritePending />}
        <DialogFooter>
          <Button ref={cancel} variant="outline" disabled={busy} onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="destructive" disabled={busy} onClick={() => void mutation.run(remove, () => { setOpen(false); onDeleted() })}>
            {busy ? 'Deleting…' : 'Delete ' + kind}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </>
}
