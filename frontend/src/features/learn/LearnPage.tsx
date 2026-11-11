import { Link } from 'react-router-dom'
import { BookOpen } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { LEARN_ARTICLES } from './articles.ts'

const CATEGORIES = ['How to use', 'Concepts'] as const

export default function LearnPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <h1 className="font-heading text-2xl font-semibold">Learn</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Short articles on Optify concepts and the steps to set up, analyze, and compare
          portfolios.
        </p>
      </div>

      {CATEGORIES.map((category) => {
        const articles = LEARN_ARTICLES.filter((article) => article.category === category)
        return (
          <section key={category} className="space-y-4">
            <div className="flex items-center gap-2">
              <BookOpen className="size-4 text-muted-foreground" />
              <h2 className="text-sm font-medium tracking-wide text-muted-foreground uppercase">
                {category}
              </h2>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {articles.map((article) => (
                <Link key={article.slug} to={`/learn/${article.slug}`} className="block">
                  <Card className="h-full transition-colors hover:bg-muted/30">
                    <CardHeader>
                      <div className="flex items-start justify-between gap-3">
                        <CardTitle className="text-lg">{article.title}</CardTitle>
                        <Badge variant="secondary">{article.minutes} min</Badge>
                      </div>
                      <CardDescription>{article.summary}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-primary">Read article</p>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}
