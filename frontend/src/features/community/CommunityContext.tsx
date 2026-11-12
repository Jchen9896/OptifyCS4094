import { createContext, useContext } from 'react'
import type { ReactNode } from 'react'
import type { CommunityApi } from './communityApi'
import { useCommunityRead } from './useCommunityRequests'

const Context = createContext<{
  api: CommunityApi
  categories: ReturnType<typeof useCommunityRead<Awaited<ReturnType<CommunityApi['categories']>>>>
  reauthenticate: () => void
} | null>(null)

export function CommunityProvider({ api, reauthenticate, children }: {
  api: CommunityApi; reauthenticate: () => void; children: ReactNode
}) {
  const categories = useCommunityRead(api.categories)
  return <Context.Provider value={{ api, categories, reauthenticate }}>{children}</Context.Provider>
}
export function useCommunity() {
  const value = useContext(Context)
  if (!value) throw Error('CommunityProvider is required')
  return value
}
