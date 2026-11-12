import { useId, useState } from 'react'
import { useDraftWarning } from './communityDrafts'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { CommunityMarkdown } from './CommunityMarkdown'
import { CommunityWritePending } from './CommunityShared'
import { limits } from './communitySchemas'
import type { Category, PostInput } from './communitySchemas'

export function MarkdownEditor({ value, onChange, maxLength, label, disabled = false }: {
  value: string; onChange: (value: string) => void; maxLength: number; label: string; disabled?: boolean
}) {
  const id = useId()
  const [preview, setPreview] = useState(false)
  return <div className="min-w-0 space-y-2">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <label htmlFor={id} className="text-sm font-medium">{label}</label>
      <div className="flex gap-1" aria-label="Editor mode">
        <Button type="button" size="sm" variant={preview ? 'ghost' : 'secondary'} aria-pressed={!preview} onClick={() => setPreview(false)}>Write</Button>
        <Button type="button" size="sm" variant={preview ? 'secondary' : 'ghost'} aria-pressed={preview} onClick={() => setPreview(true)}>Preview</Button>
      </div>
    </div>
    <textarea id={id} className={preview ? 'sr-only' : 'community-editor'} value={value}
      onChange={event => onChange(event.target.value)} maxLength={maxLength} disabled={disabled}
      aria-describedby={id + '-help'} />
    {preview && <div className="min-h-40 rounded-md border p-3" aria-label={label + ' preview'}>
      {value.trim() ? <CommunityMarkdown body={value} /> : <p className="text-sm text-muted-foreground">Nothing to preview yet.</p>}
    </div>}
    <p id={id + '-help'} className="text-xs text-muted-foreground">Markdown supported. Images are disabled. {value.length.toLocaleString()} / {maxLength.toLocaleString()}</p>
  </div>
}

export function PostEditor({ initial, categories, busy, onSubmit, onCancel }: {
  initial: PostInput; categories: Category[]; busy: boolean; onSubmit: (input: PostInput) => void; onCancel: () => void
}) {
  const [draft, setDraft] = useState<PostInput>(() => ({ title: initial.title, body: initial.body, category: initial.category }))
  const id = useId()
  const dirty = draft.title !== initial.title || draft.body !== initial.body || draft.category !== initial.category
  useDraftWarning(dirty)
  const valid = draft.title.trim() && draft.body.trim() && categories.some(category => category.slug === draft.category)
  return <form className="min-w-0 space-y-5" onSubmit={event => { event.preventDefault(); if (valid && !busy) onSubmit(draft) }}>
    <div className="space-y-2"><label htmlFor={id + '-title'} className="text-sm font-medium">Title</label>
      <Input id={id + '-title'} value={draft.title} maxLength={limits.title} disabled={busy}
        onChange={event => setDraft({ ...draft, title: event.target.value })} required /></div>
    <div className="space-y-2"><label htmlFor={id + '-category'} className="block text-sm font-medium">Category</label>
      <select id={id + '-category'} className="h-9 max-w-full rounded-md border bg-card px-3 text-sm" value={draft.category}
        disabled={busy} onChange={event => setDraft({ ...draft, category: event.target.value })} required>
        <option value="">Choose a category</option>
        {categories.map(category => <option key={category.slug} value={category.slug}>{category.label}</option>)}
      </select></div>
    <MarkdownEditor label="Post" value={draft.body} onChange={body => setDraft({ ...draft, body })} maxLength={limits.post} disabled={busy} />
    {busy && <CommunityWritePending />}
    <div className="flex flex-wrap gap-2">
      <Button type="submit" disabled={!valid || busy}>{busy ? 'Saving…' : 'Save post'}</Button>
      <Button type="button" variant="outline" disabled={busy} onClick={() => { if (!dirty || window.confirm('Discard your unsaved draft?')) onCancel() }}>Cancel</Button>
    </div>
  </form>
}

export function ReplyEditor({ initial = '', busy, onSubmit, onCancel, label = 'Your reply' }: {
  initial?: string; busy: boolean; onSubmit: (body: string) => void; onCancel?: () => void; label?: string
}) {
  const [body, setBody] = useState(initial)
  useDraftWarning(body !== initial)
  return <form className="min-w-0 space-y-3" onSubmit={event => { event.preventDefault(); if (body.trim() && !busy) onSubmit(body) }}>
    <MarkdownEditor label={label} value={body} onChange={setBody} maxLength={limits.reply} disabled={busy} />
    {busy && <CommunityWritePending />}
    <div className="flex flex-wrap gap-2">
      <Button type="submit" size="sm" disabled={!body.trim() || busy}>{busy ? 'Saving…' : 'Save reply'}</Button>
      {onCancel && <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => {
        if (body === initial || window.confirm('Discard your unsaved draft?')) onCancel()
      }}>Cancel</Button>}
    </div>
  </form>
}
