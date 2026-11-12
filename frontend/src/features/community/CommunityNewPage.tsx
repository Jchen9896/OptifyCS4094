import { useNavigate } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { useCommunity } from './CommunityContext'
import { PostEditor } from './CommunityEditor'
import { CommunityFailure } from './CommunityShared'
import { useCommunityMutation } from './useCommunityRequests'

export default function CommunityNewPage() {
  const { api, categories } = useCommunity()
  const mutation = useCommunityMutation()
  const navigate = useNavigate()
  return <div className="mx-auto w-full min-w-0 max-w-3xl space-y-6">
    <div><h1 className="text-2xl font-semibold tracking-tight">New post</h1>
      <p className="mt-1 text-sm text-muted-foreground">Share a question or an idea. Keep the discussion respectful.</p></div>
    <Card><CardContent className="min-w-0 space-y-4 py-6">
      {categories.state.kind === 'loading' && <p role="status">Loading categories…</p>}
      {categories.state.kind === 'error' && <CommunityFailure error={categories.state.error} retry={categories.reload} />}
      {mutation.state.kind === 'error' && <CommunityFailure error={mutation.state.error} write />}
      {categories.state.kind === 'ready' && <PostEditor initial={{ title: '', body: '', category: '' }}
        categories={categories.state.data} busy={mutation.state.kind === 'busy'} onCancel={() => navigate('/community')}
        onSubmit={input => void mutation.run(signal => api.createPost(input, signal), post => navigate('/community/' + post.id))} />}
    </CardContent></Card>
  </div>
}
