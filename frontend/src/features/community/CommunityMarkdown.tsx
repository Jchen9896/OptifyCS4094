import ReactMarkdown from 'react-markdown'
import './community.css'

export function safeCommunityUrl(value: string): string | undefined {
  if (!value || /[\u0000-\u0020\\]/.test(value) || value.startsWith('//')) return undefined
  const scheme = /^([a-z][a-z0-9+.-]*):/i.exec(value)
  if (scheme && !['https', 'http', 'mailto'].includes(scheme[1].toLowerCase())) return undefined
  return value
}

export function CommunityMarkdown({ body }: { body: string }) {
  return <div className="community-markdown">
    <ReactMarkdown skipHtml urlTransform={safeCommunityUrl} components={{
      img: () => null,
      a: ({ href, children }) => href ? <a href={href} rel="noreferrer noopener">{children}</a> : <span>{children}</span>,
    }}>{body}</ReactMarkdown>
  </div>
}
