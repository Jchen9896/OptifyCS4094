import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@clerk/react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/apiClient'
import { useActivePortfolio } from '../portfolio/ActivePortfolioContext.tsx'
import {
  confirmChatTool,
  createChatSession,
  sendChatMessage,
  type ChatCitation,
  type PendingTool,
} from './chatApi.ts'

type ChatBubble = {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: ChatCitation[]
  pendingTools?: PendingTool[]
}

export default function ChatPage() {
  const { getToken } = useAuth()
  const { activeId, activeLabel } = useActivePortfolio()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatBubble[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function boot() {
      setError(null)
      try {
        const token = await getToken()
        if (!token) throw new Error('Sign in to use the assistant.')
        const session = await createChatSession(token)
        if (!cancelled) setSessionId(session.id)
      } catch (caught) {
        if (!cancelled) {
          setError(
            caught instanceof ApiError
              ? `${caught.code}: ${caught.message}`
              : caught instanceof Error
                ? caught.message
                : 'Could not start chat.',
          )
        }
      }
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [getToken])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const text = draft.trim()
    if (!text || !sessionId || busy) return
    setBusy(true)
    setError(null)
    setDraft('')
    const userBubble: ChatBubble = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    }
    setMessages((current) => [...current, userBubble])
    try {
      const token = await getToken()
      if (!token) throw new Error('Sign in to use the assistant.')
      const response = await sendChatMessage(sessionId, text, activeId, token)
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.reply,
          citations: response.citations,
          pendingTools: response.pending_tools,
        },
      ])
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? `${caught.code}: ${caught.message}`
          : caught instanceof Error
            ? caught.message
            : 'Could not send message.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function onConfirm(tool: PendingTool, accept: boolean) {
    if (!sessionId || busy) return
    setBusy(true)
    setError(null)
    try {
      const token = await getToken()
      if (!token) throw new Error('Sign in to use the assistant.')
      const response = await confirmChatTool(sessionId, tool.tool_call_id, accept, token)
      setMessages((current) => [
        ...current.map((bubble) => ({
          ...bubble,
          pendingTools: bubble.pendingTools?.filter(
            (item) => item.tool_call_id !== tool.tool_call_id,
          ),
        })),
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.reply,
        },
      ])
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? `${caught.code}: ${caught.message}`
          : caught instanceof Error
            ? caught.message
            : 'Could not confirm action.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <div>
        <h1 className="font-heading text-2xl font-semibold">Assistant</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Ask about Optify workflows, metrics, and your portfolios. Write actions need your
          confirmation. Active portfolio: {activeLabel}.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card className="min-h-[28rem]">
        <CardHeader>
          <CardTitle>Conversation</CardTitle>
          <CardDescription>
            Knowledge comes from Learn articles. Your portfolios and runs are loaded live.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {messages.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Try “What does max Sharpe mean?” or “List my portfolios.”
            </p>
          ) : (
            messages.map((bubble) => (
              <div
                key={bubble.id}
                className={
                  bubble.role === 'user'
                    ? 'ml-8 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm'
                    : 'mr-8 rounded-lg border border-border bg-card px-3 py-2 text-sm'
                }
              >
                <p className="whitespace-pre-wrap">{bubble.content}</p>
                {(bubble.citations?.length ?? 0) > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {bubble.citations?.map((citation) => (
                      <Link
                        key={`${citation.slug}-${citation.heading}`}
                        to={citation.url}
                        className="rounded border border-border px-2 py-0.5 text-xs text-primary hover:underline"
                      >
                        {citation.slug}: {citation.heading}
                      </Link>
                    ))}
                  </div>
                )}
                {(bubble.pendingTools?.length ?? 0) > 0 && (
                  <div className="mt-3 space-y-2">
                    {bubble.pendingTools?.map((tool) => (
                      <div
                        key={tool.tool_call_id}
                        className="rounded border border-border bg-muted/30 px-3 py-2"
                      >
                        <p className="text-sm font-medium">{tool.summary}</p>
                        <div className="mt-2 flex gap-2">
                          <Button
                            size="sm"
                            disabled={busy}
                            onClick={() => void onConfirm(tool, true)}
                          >
                            Confirm
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busy}
                            onClick={() => void onConfirm(tool, false)}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
          {busy && (
            <div
              className="mr-8 rounded-lg border border-border bg-card px-3 py-2 text-sm text-muted-foreground"
              aria-live="polite"
              aria-label="Assistant is thinking"
            >
              <span className="inline-flex gap-1">
                <span className="animate-pulse">.</span>
                <span className="animate-pulse [animation-delay:150ms]">.</span>
                <span className="animate-pulse [animation-delay:300ms]">.</span>
              </span>
            </div>
          )}
        </CardContent>
        <CardFooter>
          <form className="flex w-full gap-2" onSubmit={onSubmit}>
            <Input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={sessionId ? 'Ask the assistant…' : 'Starting session…'}
              disabled={!sessionId || busy}
            />
            <Button type="submit" disabled={!sessionId || busy || !draft.trim()}>
              Send
            </Button>
          </form>
        </CardFooter>
      </Card>
    </div>
  )
}
