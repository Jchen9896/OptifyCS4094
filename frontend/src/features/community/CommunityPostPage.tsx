import { useCallback, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useCommunity } from './CommunityContext'
import { CommunityMarkdown } from './CommunityMarkdown'
import { PostEditor } from './CommunityEditor'
import { CommunityAuthor, CommunityFailure, DeleteCommunityItem } from './CommunityShared'
import { ReplyList } from './CommunityReplies'
import { useCommunityMutation, useCommunityRead } from './useCommunityRequests'

function PostDetail({ postId }: { postId: string }) {
  const { api, categories } = useCommunity()
  const navigate = useNavigate()
  const load = useCallback((signal: AbortSignal) => api.post(postId, signal), [api, postId])
  const post = useCommunityRead(load)
  const mutation = useCommunityMutation()
  const [editing, setEditing] = useState(false)
  if (post.state.kind === 'loading') return <p role="status">Loading discussion…</p>
  if (post.state.kind === 'error') return <CommunityFailure error={post.state.error} retry={post.reload} />
  const value = post.state.data
  const category = categories.state.kind === 'ready'
    ? categories.state.data.find(item => item.slug === value.category)?.label : undefined
  return <>
    <Card><CardContent className="min-w-0 space-y-5 py-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Badge variant="secondary">{category ?? value.category}</Badge>
        {value.is_mine && !editing && <div className="flex gap-1">
          <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>Edit post</Button>
          <DeleteCommunityItem kind="post" remove={signal => api.deletePost(postId, signal)} onDeleted={() => navigate('/community')} />
        </div>}
      </div>
      <h1 className="break-words text-2xl font-semibold tracking-tight">{value.title}</h1>
      <CommunityAuthor author={value.author} createdAt={value.created_at} editedAt={value.edited_at} />
      {editing ? <>
        {categories.state.kind === 'loading' && <p role="status">Loading categories…</p>}
        {categories.state.kind === 'error' && <CommunityFailure error={categories.state.error} retry={categories.reload} />}
        {mutation.state.kind === 'error' && <CommunityFailure error={mutation.state.error} write />}
        {categories.state.kind === 'ready' && <PostEditor initial={value} categories={categories.state.data}
          busy={mutation.state.kind === 'busy'} onCancel={() => setEditing(false)} onSubmit={input => void mutation.run(
            signal => api.updatePost(postId, input, signal), saved => { post.replace(saved); setEditing(false) },
          )} />}
      </> : <CommunityMarkdown body={value.body} />}
    </CardContent></Card>
    <section className="min-w-0 space-y-4" aria-labelledby="discussion-heading">
      <h2 id="discussion-heading" className="text-lg font-semibold">Discussion</h2>
      <ReplyList postId={postId} />
    </section>
  </>
}

export default function CommunityPostPage() {
  const { postId = '' } = useParams()
  return <div className="mx-auto w-full min-w-0 max-w-4xl space-y-6">
    <Button asChild size="sm" variant="ghost"><Link to="/community"><ArrowLeft className="size-4" />All posts</Link></Button>
    <PostDetail key={postId} postId={postId} />
  </div>
}
