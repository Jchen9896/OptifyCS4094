import { Link, Navigate, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { getLearnArticle, LEARN_ARTICLES } from './articles.ts'

export default function LearnArticlePage() {
  const { slug = '' } = useParams()
  const article = getLearnArticle(slug)

  if (!article) {
    return <Navigate to="/learn" replace />
  }

  const index = LEARN_ARTICLES.findIndex((item) => item.slug === article.slug)
  const previous = index > 0 ? LEARN_ARTICLES[index - 1] : null
  const next = index >= 0 && index < LEARN_ARTICLES.length - 1 ? LEARN_ARTICLES[index + 1] : null

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="space-y-4">
        <Button asChild variant="ghost" className="-ml-3 w-fit">
          <Link to="/learn">
            <ArrowLeft className="size-4" />
            All articles
          </Link>
        </Button>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{article.category}</Badge>
          <span className="text-xs text-muted-foreground">{article.minutes} min read</span>
        </div>
        <div>
          <h1 className="font-heading text-3xl font-semibold tracking-tight">{article.title}</h1>
          <p className="mt-3 text-sm text-muted-foreground">{article.summary}</p>
        </div>
      </div>

      <div className="space-y-8">
        {article.sections.map((section) => (
          <section key={section.heading} className="space-y-3">
            <h2 className="font-heading text-xl font-semibold">{section.heading}</h2>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph} className="text-sm leading-7 text-foreground/90">
                {paragraph}
              </p>
            ))}
          </section>
        ))}
      </div>

      <div className="flex flex-col gap-3 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
        {previous ? (
          <Button asChild variant="outline">
            <Link to={`/learn/${previous.slug}`}>Previous: {previous.title}</Link>
          </Button>
        ) : (
          <span />
        )}
        {next ? (
          <Button asChild>
            <Link to={`/learn/${next.slug}`}>Next: {next.title}</Link>
          </Button>
        ) : (
          <Button asChild variant="outline">
            <Link to="/setup">Open portfolio setup</Link>
          </Button>
        )}
      </div>
    </div>
  )
}
