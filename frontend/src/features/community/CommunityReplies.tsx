import { useCallback, useState } from 'react'
import { Button } from '@/components/ui/button'
import { useCommunity } from './CommunityContext'
import { CommunityMarkdown } from './CommunityMarkdown'
import { ReplyEditor } from './CommunityEditor'
import { CommunityAuthor, CommunityFailure, DeleteCommunityItem, PageContinuation } from './CommunityShared'
import { useCommunityMutation, useCommunityPage } from './useCommunityRequests'
import type { Reply } from './communitySchemas'

function ReplyNode({ reply, depth, update, invalidate }: {
  reply: Reply; depth: number; update: (reply: Reply) => void; invalidate: () => void
}) {
  const { api } = useCommunity()
  const [expanded, setExpanded] = useState(false)
  const [composing, setComposing] = useState(false)
  const [editing, setEditing] = useState(false)
  const [removed, setRemoved] = useState(false)
  const mutation = useCommunityMutation()
  const live = !removed && reply.deleted_at === null
  return <li className="min-w-0 space-y-3 border-t py-4 first:border-t-0">
    {live ? <>
      <CommunityAuthor author={reply.author} createdAt={reply.created_at} editedAt={reply.edited_at} />
      {editing ? <div className="space-y-3">
        {mutation.state.kind === 'error' && <CommunityFailure error={mutation.state.error} write />}
        <ReplyEditor initial={reply.body} busy={mutation.state.kind === 'busy'} label="Edit reply"
          onCancel={() => setEditing(false)} onSubmit={body => void mutation.run(
            signal => api.updateReply(reply.post_id, reply.id, body, signal),
            saved => { update(saved); setEditing(false) },
          )} />
      </div> : <CommunityMarkdown body={reply.body} />}
    </> : <p className="text-sm italic text-muted-foreground">This reply was deleted.</p>}
    <div className="flex flex-wrap gap-1">
      {!expanded && <Button size="sm" variant="ghost" onClick={() => setExpanded(true)}>Show replies</Button>}
      <Button size="sm" variant="ghost" onClick={() => { setExpanded(true); setComposing(true) }}>Reply</Button>
      {live && reply.is_mine && !editing && <>
        <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>Edit</Button>
        <DeleteCommunityItem kind="reply" remove={signal => api.deleteReply(reply.post_id, reply.id, signal)} onDeleted={() => {
          setRemoved(true)
          invalidate()
        }} />
      </>}
    </div>
    {expanded && <div className={depth < 3 ? 'min-w-0 border-l pl-3 sm:pl-5' : 'min-w-0'}>
      <ReplyList postId={reply.post_id} parentId={reply.id} depth={depth + 1} composing={composing} onComposed={() => setComposing(false)} />
    </div>}
  </li>
}

export function ReplyList({ postId, parentId = null, depth = 0, composing = true, onComposed }: {
  postId: string; parentId?: string | null; depth?: number; composing?: boolean; onComposed?: () => void
}) {
  const { api } = useCommunity()
  const load = useCallback((cursor: string | null, signal: AbortSignal) => api.replies(postId, parentId, cursor, signal), [api, postId, parentId])
  const page = useCommunityPage(load)
  const mutation = useCommunityMutation()
  const [editorVersion, setEditorVersion] = useState(0)
  const rows = page.state.kind === 'ready' ? [...page.state.data.items].sort((a, b) =>
    a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id)) : []
  return <div className="min-w-0 space-y-4">
    {rows.length > 0 && <ul className="min-w-0" aria-label={parentId ? 'Replies to reply' : 'Discussion replies'}>
      {rows.map(reply => <ReplyNode key={reply.id} reply={reply} depth={depth} update={page.invalidate} invalidate={() => page.invalidate()} />)}
    </ul>}
    {page.state.kind === 'ready' && rows.length === 0 && <p className="text-sm text-muted-foreground">No replies yet.</p>}
    <PageContinuation state={page.state} more={page.more} reload={page.reload} />
    {composing && page.state.kind === 'ready' && <div className="min-w-0 space-y-3 rounded-md border bg-card p-3 sm:p-4">
      {mutation.state.kind === 'error' && <CommunityFailure error={mutation.state.error} write />}
      <ReplyEditor key={editorVersion} busy={mutation.state.kind === 'busy'} onCancel={onComposed}
        onSubmit={body => void mutation.run(signal => api.createReply(postId, parentId, body, signal), saved => {
          page.invalidate(saved)
          setEditorVersion(version => version + 1)
          onComposed?.()
        })} />
    </div>}
  </div>
}
