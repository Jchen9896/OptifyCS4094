import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useAuth } from '@clerk/react'
import { ApiError } from '@/lib/apiClient'
import { clearLastOptimizationRun } from '../optimization/optimizationApi.ts'
import {
  deletePortfolio,
  listPortfolios,
  readPortfolio,
  restorePortfolio,
  type PortfolioDraft,
  type PortfolioSummary,
  type SavedPortfolio,
} from './portfolioApi.ts'

type ActivePortfolioContextValue = {
  portfolios: PortfolioSummary[]
  activeId: string | null
  activeLabel: string
  draftRevision: number
  pendingDraft: PortfolioDraft | null
  busy: boolean
  error: string | null
  refresh: () => Promise<void>
  selectPortfolio: (id: string) => Promise<void>
  removePortfolio: (id: string) => Promise<void>
  startNew: () => void
  noteSaved: (saved: SavedPortfolio) => void
}

const ActivePortfolioContext = createContext<ActivePortfolioContextValue | null>(null)

function blankDraft(): PortfolioDraft {
  return {
    portfolioName: '',
    initialCapital: 0,
    startDate: '',
    endDate: '',
    strategy: '',
    maxWeightPercent: 0,
    riskFreePercent: 0,
    targetReturnPercent: null,
    targetVolatilityPercent: null,
    holdings: [],
    referencePrices: {},
  }
}

export function ActivePortfolioProvider({ children }: { children: ReactNode }) {
  const { isLoaded, isSignedIn, getToken, userId } = useAuth()
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [activeLabel, setActiveLabel] = useState('New portfolio')
  const [pendingDraft, setPendingDraft] = useState<PortfolioDraft | null>(null)
  const [draftRevision, setDraftRevision] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const token = useCallback(async (fresh = false) => {
    const value = await getToken(fresh ? { skipCache: true } : undefined)
    if (!value) throw new Error('Sign in to use saved portfolios.')
    return value
  }, [getToken])

  const refresh = useCallback(async () => {
    if (!isLoaded) {
      return
    }
    if (!isSignedIn) {
      setPortfolios([])
      setError(null)
      return
    }
    setBusy(true)
    setError(null)
    let lastError: unknown = null
    try {
      // Clerk can hand a stale/incomplete JWT for a beat after sign-in; retry with a fresh token.
      for (let attempt = 0; attempt < 4; attempt += 1) {
        try {
          setPortfolios(await listPortfolios(await token(attempt > 0)))
          setError(null)
          return
        } catch (caught) {
          lastError = caught
          const unauthorized = caught instanceof ApiError && caught.status === 401
          if (!unauthorized || attempt === 3) {
            break
          }
          await new Promise((resolve) => window.setTimeout(resolve, 250 * (attempt + 1)))
        }
      }
      setPortfolios([])
      if (lastError instanceof ApiError && lastError.status === 401) {
        setError(
          lastError.message === 'Clerk session is missing the email claim'
            ? 'Clerk is missing the email session claim. In Clerk → Sessions → Customize session token, set {"email":"{{user.primary_email_address}}"}, save, then sign out and sign in again.'
            : `Could not verify your session with the API (${lastError.message}). Confirm CLERK_JWT_KEY / CLERK_ISSUER match this Clerk app, then sign out and sign in again.`,
        )
      } else {
        setError(
          lastError instanceof ApiError
            ? `${lastError.code}: ${lastError.message}`
            : lastError instanceof Error
              ? lastError.message
              : 'Could not list portfolios.',
        )
      }
    } finally {
      setBusy(false)
    }
  }, [isLoaded, isSignedIn, token])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const startNew = useCallback(() => {
    setActiveId(null)
    setActiveLabel('New portfolio')
    setPendingDraft(blankDraft())
    setDraftRevision((current) => current + 1)
    setError(null)
  }, [])

  const selectPortfolio = useCallback(
    async (id: string) => {
      const summary = portfolios.find((row) => row.id === id)
      setActiveId(id)
      setActiveLabel(summary?.name ?? 'Portfolio')
      setBusy(true)
      setError(null)
      try {
        const restored = restorePortfolio(await readPortfolio(await token(), id))
        setActiveLabel(restored.portfolioName)
        setPendingDraft(restored)
        setDraftRevision((current) => current + 1)
      } catch (caught) {
        setPendingDraft(null)
        setError(
          caught instanceof ApiError
            ? `${caught.code}: ${caught.message}`
            : caught instanceof Error
              ? caught.message
              : 'Could not load portfolio setup.',
        )
      } finally {
        setBusy(false)
      }
    },
    [portfolios, token],
  )

  const removePortfolio = useCallback(
    async (id: string) => {
      setBusy(true)
      setError(null)
      try {
        await deletePortfolio(await token(), id)
        clearLastOptimizationRun(userId ?? null, id)
        setPortfolios((current) => current.filter((row) => row.id !== id))
        if (activeId === id) {
          setActiveId(null)
          setActiveLabel('New portfolio')
          setPendingDraft(blankDraft())
          setDraftRevision((current) => current + 1)
        }
      } catch (caught) {
        setError(
          caught instanceof ApiError
            ? `${caught.code}: ${caught.message}`
            : caught instanceof Error
              ? caught.message
              : 'Could not delete portfolio.',
        )
        throw caught
      } finally {
        setBusy(false)
      }
    },
    [activeId, token, userId],
  )

  const noteSaved = useCallback((saved: SavedPortfolio) => {
    setPortfolios((current) => [saved, ...current.filter((row) => row.id !== saved.id)])
    setActiveId(saved.id)
    setActiveLabel(saved.name)
    setError(null)
    try {
      setPendingDraft(restorePortfolio(saved))
      setDraftRevision((current) => current + 1)
    } catch {
      // Holdings-only responses without setup stay on the prior draft.
    }
  }, [])

  const value = useMemo(
    () => ({
      portfolios,
      activeId,
      activeLabel,
      draftRevision,
      pendingDraft,
      busy,
      error,
      refresh,
      selectPortfolio,
      removePortfolio,
      startNew,
      noteSaved,
    }),
    [
      portfolios,
      activeId,
      activeLabel,
      draftRevision,
      pendingDraft,
      busy,
      error,
      refresh,
      selectPortfolio,
      removePortfolio,
      startNew,
      noteSaved,
    ],
  )

  return <ActivePortfolioContext.Provider value={value}>{children}</ActivePortfolioContext.Provider>
}

export function useActivePortfolio() {
  const value = useContext(ActivePortfolioContext)
  if (!value) throw new Error('useActivePortfolio requires ActivePortfolioProvider.')
  return value
}
