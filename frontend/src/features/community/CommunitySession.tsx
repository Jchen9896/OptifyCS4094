import { useEffect, useRef, useState } from 'react'
import { useAuth, useClerk } from '@clerk/react'
import { Outlet } from 'react-router-dom'
import { createCommunityApi } from './communityApi'
import type { CommunityApi } from './communityApi'
import { CommunityProvider } from './CommunityContext'
import { requestCommunityLeave } from './communityDrafts'

function SessionClient() {
  const { getToken } = useAuth()
  const { signOut } = useClerk()
  const token = useRef(getToken)
  token.current = getToken
  const [api, setApi] = useState<CommunityApi | null>(null)
  useEffect(() => {
    const client = createCommunityApi({ getToken: () => token.current() })
    setApi(client)
    return () => client.dispose()
  }, [])
  if (!api) return <p role="status">Loading Community…</p>
  return <CommunityProvider api={api} reauthenticate={() => {
    if (requestCommunityLeave() && window.confirm('Sign out and sign in again? Unsaved drafts will be lost.')) void signOut({ redirectUrl: '/login' })
  }}><Outlet /></CommunityProvider>
}

export default function CommunitySession() {
  const { userId, sessionId } = useAuth()
  return <SessionClient key={JSON.stringify([userId, sessionId])} />
}
