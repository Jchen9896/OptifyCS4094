import { useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Plus, MessagesSquare } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useCommunity } from './CommunityContext'
import { CommunityMarkdown } from './CommunityMarkdown'
import { CommunityAuthor, CommunityFailure, PageContinuation } from './CommunityShared'
import { useCommunityPage } from './useCommunityRequests'

function Feed({ category }: { category: string }) {
  const { api, categories } = useCommunity()
  const load = useCallback((cursor: string | null, signal: AbortSignal) => api.posts(category, cursor, signal), [api, category])
  const page = useCommunityPage(load)
  const labels = categories.state.kind === 'ready' ? categories.state.data : []
  return <div className="space-y-4">
    {page.state.kind === 'ready' && page.state.data.items.length === 0 && <Card>
      <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
        <MessagesSquare className="size-8 text-muted-foreground" />
        <h2 className="text-lg font-medium">Start a conversation</h2>
        <p className="max-w-sm text-sm text-muted-foreground">No posts here yet. Ask a question or share an idea with the community.</p>
        <Button asChild><Link to="/community/new">Create a post</Link></Button>
      </CardContent>
    </Card>}
    {page.state.kind === 'ready' && page.state.data.items.map(post => <Card key={post.id}>
      <CardContent className="min-w-0 space-y-4 py-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{labels.find(item => item.slug === post.category)?.label ?? post.category}</Badge>
        </div>
        <h2 className="break-words text-lg font-semibold tracking-tight">
          <Link className="rounded-sm hover:text-primary focus-visible:outline-2 focus-visible:outline-ring" to={'/community/' + post.id}>{post.title}</Link>
        </h2>
        <div className="line-clamp-2 min-w-0 text-muted-foreground"><CommunityMarkdown body={post.body.split(/\n\s*\n/, 1)[0]} /></div>
        <CommunityAuthor author={post.author} createdAt={post.created_at} editedAt={post.edited_at} />
      </CardContent>
    </Card>)}
    <PageContinuation state={page.state} more={page.more} reload={page.reload} />
  </div>
}

export default function CommunityFeedPage() {
  const [params, setParams] = useSearchParams()
  const category = params.get('category') ?? ''
  const { categories } = useCommunity()
  return <div className="mx-auto w-full min-w-0 max-w-4xl space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><h1 className="text-2xl font-semibold tracking-tight">Community</h1>
        <p className="mt-1 text-sm text-muted-foreground">A place to ask, learn, and share investing ideas.</p></div>
      <Button asChild><Link to="/community/new"><Plus className="size-4" />New post</Link></Button>
    </div>
    {categories.state.kind === 'error' && <CommunityFailure error={categories.state.error} retry={categories.reload} />}
    <nav aria-label="Post categories" className="flex flex-wrap gap-2">
      <Button size="sm" variant={!category ? 'default' : 'outline'} aria-pressed={!category} onClick={() => setParams({})}>All posts</Button>
      {categories.state.kind === 'ready' && categories.state.data.map(item =>
        <Button key={item.slug} size="sm" variant={category === item.slug ? 'default' : 'outline'} aria-pressed={category === item.slug}
          onClick={() => setParams({ category: item.slug })}>{item.label}</Button>)}
    </nav>
    <Feed key={category} category={category} />
  </div>
}
