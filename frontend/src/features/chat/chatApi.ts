import { fetchJson } from '../../lib/apiClient.ts'

export type ChatCitation = {
  slug: string
  heading: string
  url: string
}

export type PendingTool = {
  tool_call_id: string
  tool_name: string
  summary: string
  arguments: Record<string, unknown>
}

export type ChatSession = {
  id: string
  created_at: string
}

export type ChatMessageResponse = {
  session_id: string
  reply: string
  citations: ChatCitation[]
  pending_tools: PendingTool[]
}

export type ChatConfirmResponse = {
  session_id: string
  accepted: boolean
  reply: string
  result: Record<string, unknown> | null
}

export async function createChatSession(token: string): Promise<ChatSession> {
  return fetchJson('/api/chat/sessions', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function sendChatMessage(
  sessionId: string,
  content: string,
  activePortfolioId: string | null,
  token: string,
): Promise<ChatMessageResponse> {
  return fetchJson(`/api/chat/sessions/${encodeURIComponent(sessionId)}/messages`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      content,
      active_portfolio_id: activePortfolioId,
    }),
  })
}

export async function confirmChatTool(
  sessionId: string,
  toolCallId: string,
  accept: boolean,
  token: string,
): Promise<ChatConfirmResponse> {
  return fetchJson(`/api/chat/sessions/${encodeURIComponent(sessionId)}/confirm`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ tool_call_id: toolCallId, accept }),
  })
}
