// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CommunityMarkdown, safeCommunityUrl } from '../../src/features/community/CommunityMarkdown'
import { PostEditor, ReplyEditor } from '../../src/features/community/CommunityEditor'

afterEach(cleanup)
describe('safe Markdown and drafts', () => {
  it.each(['javascript:alert(1)', 'data:text/html,hello', '//tracker.test/x', '\\tracker.test', 'java\nscript:alert(1)'])('rejects unsafe URL %s', value => {
    expect(safeCommunityUrl(value)).toBeUndefined()
  })
  it('renders CommonMark without raw HTML or remote images', () => {
    const { container } = render(<CommunityMarkdown body={'# Hello\n\n**strong** [safe](https://example.test) [bad](javascript:alert)\n\n![tracking](https://tracker.test/x)\n\n<script>alert(1)</script>'} />)
    expect(screen.getByRole('heading', { name: 'Hello' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'safe' }).getAttribute('href')).toBe('https://example.test')
    expect(screen.queryByRole('link', { name: 'bad' })).toBeNull()
    expect(container.querySelector('script, img')).toBeNull()
  })
  it('preserves a failed-write draft while switching preview modes', () => {
    const submit = vi.fn()
    render(<PostEditor initial={{ title: '', body: '', category: '' }} categories={[{ slug: 'question', label: 'Questions' }]} busy={false} onSubmit={submit} onCancel={() => {}} />)
    expect(screen.getByRole('button', { name: 'Save post' }).hasAttribute('disabled')).toBe(true)
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Title' } })
    fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'question' } })
    fireEvent.change(screen.getByLabelText('Post'), { target: { value: '**Draft**' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect(screen.getByText('Draft')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Save post' }))
    expect(submit).toHaveBeenCalledWith({ title: 'Title', body: '**Draft**', category: 'question' })
    fireEvent.click(screen.getByRole('button', { name: 'Write' }))
    expect(screen.getByLabelText<HTMLTextAreaElement>('Post').value).toBe('**Draft**')
  })
  it('uses authoritative text limits and blocks duplicate submission while busy', () => {
    const submit = vi.fn()
    render(<ReplyEditor busy onSubmit={submit} initial="Draft" />)
    expect(screen.getByLabelText('Your reply').getAttribute('maxlength')).toBe('4000')
    expect(screen.getByRole('button', { name: 'Saving…' }).hasAttribute('disabled')).toBe(true)
    fireEvent.submit(screen.getByRole('button', { name: 'Saving…' }).closest('form')!)
    expect(submit).not.toHaveBeenCalled()
  })
})
