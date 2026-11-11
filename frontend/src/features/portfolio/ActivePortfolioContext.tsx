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
    holdings: [],
    referencePrices: {},
  }
}

export function ActivePortfolioProvider({ children }: { children: ReactNode }) {
  const { isSignedIn, getToken, userId } = useAuth()
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [activeLabel, setActiveLabel] = useState('New portfolio')
  const [pendingDraft, setPendingDraft] = useState<PortfolioDraft | null>(null)
  const [draftRevision, setDraftRevision] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const token = useCallback(async () => {
    const value = await getToken()
    if (!value) throw new Error('Sign in to use saved portfolios.')
    return value
  }, [getToken])

  const refresh = useCallback(async () => {
    if (!isSignedIn) {
      setPortfolios([])
      return
    }
    setBusy(true)
    setError(null)
    try {
      setPortfolios(await listPortfolios(await token()))
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? `${caught.code}: ${caught.message}`
          : caught instanceof Error
            ? caught.message
            : 'Could not list portfolios.',
      )
    } finally {
      setBusy(false)
    }
  }, [isSignedIn, token])

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
