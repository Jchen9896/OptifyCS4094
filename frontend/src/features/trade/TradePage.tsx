import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '@clerk/react'
import { Link } from 'react-router-dom'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ApiError } from '@/lib/apiClient'
import { cn } from '@/lib/utils'
import { formatWeight } from '@/lib/formatters.ts'
import {
  listOptimizationRuns,
  loadLastOptimizationRun,
  readOptimizationRun,
  type OptimizationResult,
  type OptimizationRunSummary,
} from '../optimization/optimizationApi.ts'
import { useActivePortfolio } from '../portfolio/ActivePortfolioContext.tsx'
import { BROKERAGE_OPTIONS, type BrokerageId } from '../portfolio/brokerageImport.ts'
import PortfolioSwitcher from '../portfolio/components/PortfolioSwitcher.tsx'
import RunSwitcher from '../portfolio/components/RunSwitcher.tsx'
import { readPortfolio } from '../portfolio/portfolioApi.ts'
import {
  listBrokerageCredentials,
  type BrokerageCredentialStatus,
} from '../settings/settingsApi.ts'
import {
  listSchwabTradeAccounts,
  submitSchwabOrders,
  type SchwabAccountSummary,
  type SubmittedOrderResult,
} from './tradeApi.ts'
import {
  plannedTradesFromWeights,
  summarizeTrades,
  wholeShares,
  type TradeSide,
} from './tradePlan.ts'

type TradeRun = {
  result: OptimizationResult
  prices: Record<string, number>
  capital: number
  currentWeights: Record<string, number>
  currentQuantities: Record<string, number>
  names: Record<string, string>
}

type ReviewOrder = {
  id: string
  symbol: string
  name: string
  side: 'buy' | 'sell'
  quantity: number
  price: number | null
  currentWeight: number
  targetWeight: number
}

type BrokerageRouteStatus = 'ready' | 'needs_auth' | 'coming_soon'

function formatShares(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 })
}

function formatMoney(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return '—'
  return value.toLocaleString(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  })
}

function sideBadge(side: TradeSide) {
  if (side === 'buy') {
    return (
      <Badge className="border-transparent bg-[#568ea3] text-white hover:bg-[#568ea3]">
        BUY
      </Badge>
    )
  }
  if (side === 'sell') {
    return <Badge variant="destructive">SELL</Badge>
  }
  return <Badge variant="outline">HOLD</Badge>
}

function maskAccountNumber(value: string): string {
  const cleaned = value.trim()
  if (cleaned.length <= 4) return cleaned
  return `••••${cleaned.slice(-4)}`
}

function brokerageLabel(id: BrokerageId): string {
  return BROKERAGE_OPTIONS.find((row) => row.id === id)?.label ?? id
}

function routeStatusFor(
  brokerage: BrokerageId,
  credentials: BrokerageCredentialStatus[],
): BrokerageRouteStatus {
  const option = BROKERAGE_OPTIONS.find((row) => row.id === brokerage)
  if (!option?.available) return 'coming_soon'
  const row = credentials.find((item) => item.provider === brokerage)
  return row?.authorized ? 'ready' : 'needs_auth'
}

function ordersFromTrades(
  trades: ReturnType<typeof plannedTradesFromWeights>,
  runKey: string,
): ReviewOrder[] {
  return trades
    .filter((trade) => trade.side !== 'hold' && Math.abs(trade.deltaQty) >= 1)
    .map((trade) => ({
      id: `${runKey}-${trade.symbol}-${trade.side}`,
      symbol: trade.symbol,
      name: trade.name,
      side: trade.side as 'buy' | 'sell',
      quantity: wholeShares(Math.abs(trade.deltaQty)),
      price: trade.price,
      currentWeight: trade.currentWeight,
      targetWeight: trade.targetWeight,
    }))
    .filter((order) => order.quantity >= 1)
}

export default function TradePage() {
  const { getToken, userId } = useAuth()
  const { activeId, activeLabel } = useActivePortfolio()

  const [runSummaries, setRunSummaries] = useState<OptimizationRunSummary[]>([])
  const [selectedRunId, setSelectedRunId] = useState('')
  const [tradeRun, setTradeRun] = useState<TradeRun | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [orders, setOrders] = useState<ReviewOrder[]>([])
  const [qtyDrafts, setQtyDrafts] = useState<Record<string, string>>({})

  const [credentials, setCredentials] = useState<BrokerageCredentialStatus[]>([])
  const [brokerage, setBrokerage] = useState<BrokerageId>('schwab')
  const [accounts, setAccounts] = useState<SchwabAccountSummary[]>([])
  const [accountHash, setAccountHash] = useState('')
  const [accountsBusy, setAccountsBusy] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitNote, setSubmitNote] = useState<string | null>(null)
  const [submitResults, setSubmitResults] = useState<SubmittedOrderResult[] | null>(null)

  const token = useCallback(async () => {
    const value = await getToken()
    if (!value) throw new Error('Sign in to use Trade.')
    return value
  }, [getToken])

  const routeStatus = routeStatusFor(brokerage, credentials)
  const canRouteLive = routeStatus === 'ready' && brokerage === 'schwab' && Boolean(accountHash)
  const selectedAccount = accounts.find((row) => row.account_hash === accountHash) ?? null

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const rows = await listBrokerageCredentials(await token())
        if (cancelled) return
        setCredentials(rows)
        const firstReady = BROKERAGE_OPTIONS.find((option) =>
          rows.some((row) => row.provider === option.id && row.authorized),
        )
        if (firstReady) {
          setBrokerage((current) => {
            const currentReady = rows.some(
              (row) => row.provider === current && row.authorized,
            )
            return currentReady ? current : firstReady.id
          })
        }
      } catch {
        if (!cancelled) setCredentials([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (brokerage !== 'schwab' || routeStatus !== 'ready') {
        setAccounts([])
        setAccountHash('')
        return
      }
      setAccountsBusy(true)
      try {
        const schwabAccounts = await listSchwabTradeAccounts(await token())
        if (cancelled) return
        setAccounts(schwabAccounts)
        setAccountHash((current) =>
          current && schwabAccounts.some((row) => row.account_hash === current)
            ? current
            : schwabAccounts[0]?.account_hash ?? '',
        )
      } catch {
        if (!cancelled) {
          setAccounts([])
          setAccountHash('')
        }
      } finally {
        if (!cancelled) setAccountsBusy(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [brokerage, routeStatus, token])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!activeId) {
        setRunSummaries([])
        setSelectedRunId('')
        setTradeRun(null)
        return
      }
      setLoading(true)
      setError(null)
      try {
        const rows = await listOptimizationRuns(activeId, await token())
        if (cancelled) return
        setRunSummaries(rows)
        setSelectedRunId((current) =>
          current && rows.some((row) => row.id === current) ? current : rows[0]?.id ?? '',
        )
      } catch (caught) {
        if (cancelled) return
        setRunSummaries([])
        setSelectedRunId('')
        setError(
          caught instanceof ApiError
            ? caught.message
            : caught instanceof Error
              ? caught.message
              : 'Could not load optimization runs.',
        )
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [activeId, token])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!activeId || !selectedRunId) {
        if (!activeId) {
          const session = loadLastOptimizationRun(userId ?? null, null)
          if (session) {
            setTradeRun({
              result: session.result,
              prices: session.referencePrices ?? {},
              capital: session.initialCapital ?? session.result.initial_capital,
              currentWeights: Object.fromEntries(
                session.holdings.map((holding) => [holding.symbol, holding.weightPercent / 100]),
              ),
              currentQuantities: Object.fromEntries(
                session.holdings.map((holding) => [holding.symbol, holding.quantity ?? 0]),
              ),
              names: Object.fromEntries(
                session.holdings.map((holding) => [holding.symbol, holding.name]),
              ),
            })
          } else {
            setTradeRun(null)
          }
        } else {
          setTradeRun(null)
        }
        return
      }
      setLoading(true)
      setError(null)
      try {
        const auth = await token()
        const [detail, portfolio] = await Promise.all([
          readOptimizationRun(activeId, selectedRunId, auth),
          readPortfolio(auth, activeId).catch(() => null),
        ])
        if (cancelled) return
        const capital =
          detail.params.initial_capital ?? detail.result.initial_capital ?? 0
        const prices = {
          ...(portfolio?.setup?.reference_prices ?? {}),
          ...(detail.params.reference_prices ?? {}),
        }
        const weightList = detail.params.current_weights ?? []
        const currentWeights = Object.fromEntries(
          detail.params.tickers.map((ticker, index) => [ticker, weightList[index] ?? 0]),
        )
        const currentQuantities = Object.fromEntries(
          (portfolio?.holdings ?? []).map((holding) => [
            holding.symbol,
            Number(holding.quantity),
          ]),
        )
        const names = Object.fromEntries(
          (portfolio?.holdings ?? []).map((holding) => [holding.symbol, holding.name]),
        )
        for (const ticker of detail.params.tickers) {
          if (!names[ticker]) names[ticker] = ticker
        }
        setTradeRun({
          result: detail.result,
          prices,
          capital,
          currentWeights,
          currentQuantities,
          names,
        })
      } catch (caught) {
        if (cancelled) return
        setTradeRun(null)
        setError(
          caught instanceof ApiError
            ? caught.message
            : caught instanceof Error
              ? caught.message
              : 'Could not load the selected run.',
        )
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [activeId, selectedRunId, token, userId])

  const planned = useMemo(() => {
    if (!tradeRun) return []
    const symbols = Array.from(
      new Set([
        ...Object.keys(tradeRun.result.weights),
        ...Object.keys(tradeRun.currentWeights),
      ]),
    )
    return plannedTradesFromWeights({
      symbols,
      names: tradeRun.names,
      currentWeights: tradeRun.currentWeights,
      targetWeights: tradeRun.result.weights,
      currentQuantities: tradeRun.currentQuantities,
      prices: tradeRun.prices,
      capital: tradeRun.capital,
    })
  }, [tradeRun])

  const runKey = selectedRunId || 'session'

  useEffect(() => {
    const next = ordersFromTrades(planned, runKey)
    setOrders(next)
    setQtyDrafts(
      Object.fromEntries(next.map((order) => [order.id, String(order.quantity)])),
    )
    setSubmitResults(null)
    setSubmitNote(null)
  }, [planned, runKey])

  const summary = useMemo(() => {
    let buys = 0
    let sells = 0
    let buyNotional = 0
    let sellNotional = 0
    let buyShares = 0
    let sellShares = 0
    for (const order of orders) {
      const notional =
        order.price != null && order.price > 0 ? order.quantity * order.price : 0
      if (order.side === 'buy') {
        buys += 1
        buyShares += order.quantity
        buyNotional += notional
      } else {
        sells += 1
        sellShares += order.quantity
        sellNotional += notional
      }
    }
    return {
      buys,
      sells,
      buyShares,
      sellShares,
      buyNotional,
      sellNotional,
      netNotional: buyNotional - sellNotional,
      orderCount: orders.length,
    }
  }, [orders])

  const planSummary = useMemo(() => summarizeTrades(planned), [planned])

  function commitQuantity(orderId: string) {
    const raw = qtyDrafts[orderId] ?? ''
    if (!/^\d+$/.test(raw)) {
      const existing = orders.find((row) => row.id === orderId)
      if (existing) {
        setQtyDrafts((current) => ({
          ...current,
          [orderId]: String(existing.quantity),
        }))
      }
      return
    }
    const quantity = wholeShares(Number(raw))
    if (quantity < 1) {
      const existing = orders.find((row) => row.id === orderId)
      if (existing) {
        setQtyDrafts((current) => ({
          ...current,
          [orderId]: String(existing.quantity),
        }))
      }
      return
    }
    setOrders((current) =>
      current.map((row) => (row.id === orderId ? { ...row, quantity } : row)),
    )
    setQtyDrafts((current) => ({ ...current, [orderId]: String(quantity) }))
  }

  function resetOrders() {
    const next = ordersFromTrades(planned, runKey)
    setOrders(next)
    setQtyDrafts(
      Object.fromEntries(next.map((order) => [order.id, String(order.quantity)])),
    )
    setSubmitResults(null)
    setSubmitNote(null)
  }

  async function handleSubmit() {
    if (orders.length === 0) {
      setSubmitNote('No orders to submit.')
      return
    }
    if (routeStatus === 'coming_soon') {
      setSubmitNote(`${brokerageLabel(brokerage)} order routing is not available yet.`)
      return
    }
    if (routeStatus === 'needs_auth') {
      setSubmitNote(`Connect ${brokerageLabel(brokerage)} in Settings before submitting.`)
      return
    }
    if (brokerage !== 'schwab') {
      setSubmitNote(`${brokerageLabel(brokerage)} live routing is not wired yet.`)
      return
    }
    if (!accountHash) {
      setSubmitNote('Select a brokerage account to route these orders.')
      return
    }
    const invalid = orders.find((order) => !Number.isInteger(order.quantity) || order.quantity < 1)
    if (invalid) {
      setSubmitNote('Every order quantity must be a whole number of at least 1 share.')
      return
    }

    setSubmitting(true)
    setSubmitNote(null)
    setSubmitResults(null)
    setError(null)
    try {
      const response = await submitSchwabOrders(await token(), {
        account_hash: accountHash,
        orders: orders.map((order) => ({
          symbol: order.symbol,
          side: order.side,
          quantity: order.quantity,
        })),
      })
      setSubmitResults(response.results)
      const accepted = response.results.filter((row) => row.status === 'accepted').length
      const rejected = response.results.length - accepted
      const accountLabel = response.account_number
        ? maskAccountNumber(response.account_number)
        : 'selected account'
      setSubmitNote(
        rejected === 0
          ? `Submitted ${accepted} order${accepted === 1 ? '' : 's'} to ${brokerageLabel(brokerage)} ${accountLabel}.`
          : `Submitted with ${accepted} accepted and ${rejected} rejected.`,
      )
      if (accepted > 0) {
        const acceptedIds = new Set(
          response.results
            .filter((row) => row.status === 'accepted')
            .map((row) => `${row.symbol}-${row.side}`),
        )
        setOrders((current) =>
          current.filter((order) => !acceptedIds.has(`${order.symbol}-${order.side}`)),
        )
        setQtyDrafts((current) => {
          const next = { ...current }
          for (const order of orders) {
            if (acceptedIds.has(`${order.symbol}-${order.side}`)) {
              delete next[order.id]
            }
          }
          return next
        })
      }
    } catch (caught) {
      setSubmitNote(
        caught instanceof ApiError
          ? caught.message
          : caught instanceof Error
            ? caught.message
            : 'Could not submit orders.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  const destinationHint =
    routeStatus === 'needs_auth'
      ? `Authorize ${brokerageLabel(brokerage)} in Settings, then pick the account that should receive these orders.`
      : accountsBusy
        ? 'Loading accounts…'
        : accounts.length === 0
          ? 'Authorized, but no tradeable accounts were returned.'
          : 'Orders submit only to the account selected below.'

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">Trade</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Build whole-share rebalance orders from a run, choose which brokerage account to route
            them to, then review and submit.
          </p>
        </div>
        <div className="w-full min-w-[20rem] max-w-xl shrink-0 space-y-3">
          <PortfolioSwitcher
            label="Portfolio"
            className="w-full max-w-none sm:items-stretch"
          />
          {activeId && (
            <RunSwitcher
              label="Run"
              runs={runSummaries}
              selectedRunId={selectedRunId}
              busy={loading}
              onSelect={setSelectedRunId}
              className="w-full max-w-none sm:items-stretch"
            />
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-border/70 bg-muted/40">
            <CardDescription className="text-xs tracking-wide uppercase">
              Order destination
            </CardDescription>
            <CardTitle className="text-lg">Brokerage & account</CardTitle>
            <CardDescription>
              Connect multiple brokerages in Settings, then pick the firm and account for this
              ticket.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field>
                <FieldLabel>Brokerage</FieldLabel>
                <Select
                  value={brokerage}
                  onValueChange={(value) => {
                    if (!value) return
                    setBrokerage(value as BrokerageId)
                    setSubmitNote(null)
                    setSubmitResults(null)
                  }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select brokerage" />
                  </SelectTrigger>
                  <SelectContent>
                    {BROKERAGE_OPTIONS.filter((option) => option.available).map((option) => {
                      const status = routeStatusFor(option.id, credentials)
                      return (
                        <SelectItem key={option.id} value={option.id}>
                          {option.label}
                          {status === 'ready' ? ' · connected' : ' · connect in Settings'}
                        </SelectItem>
                      )
                    })}
                  </SelectContent>
                </Select>
                <FieldDescription>
                  Only brokerages with live routing appear here. Connect more in Settings.
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel>Account</FieldLabel>
                {brokerage === 'schwab' && routeStatus === 'ready' && accounts.length > 0 ? (
                  <Select
                    value={accountHash}
                    onValueChange={(value) => setAccountHash(value ?? '')}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select account" />
                    </SelectTrigger>
                    <SelectContent>
                      {accounts.map((account) => (
                        <SelectItem key={account.account_hash} value={account.account_hash}>
                          {brokerageLabel(brokerage)} {maskAccountNumber(account.account_number)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className="flex h-8 items-center rounded-lg border border-dashed border-border px-2.5 text-sm text-muted-foreground">
                    {routeStatus === 'needs_auth'
                      ? 'Connect brokerage first'
                      : accountsBusy
                        ? 'Loading…'
                        : 'No accounts found'}
                  </div>
                )}
                <FieldDescription>{destinationHint}</FieldDescription>
              </Field>
            </div>
          </CardContent>
          <CardFooter className="justify-between gap-3">
            <p className="text-xs text-muted-foreground">
              {selectedAccount
                ? `Routing to ${brokerageLabel(brokerage)} ${maskAccountNumber(selectedAccount.account_number)}`
                : 'No live account selected'}
            </p>
            <Button asChild variant="outline" size="sm">
              <Link to="/settings">Manage connections</Link>
            </Button>
          </CardFooter>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 lg:content-start">
          <Card size="sm">
            <CardHeader>
              <CardDescription className="text-xs tracking-wide uppercase">
                Working ticket
              </CardDescription>
              <CardTitle className="text-2xl tabular-nums">{summary.orderCount}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {summary.buys} buy · {summary.sells} sell
                {planSummary.holds > 0 ? ` · ${planSummary.holds} hold` : ''}
              </p>
            </CardContent>
          </Card>
          <Card size="sm">
            <CardHeader>
              <CardDescription className="text-xs tracking-wide uppercase">Buy</CardDescription>
              <CardTitle className="text-2xl tabular-nums text-[#3f6d7e]">
                {formatMoney(summary.buyNotional)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {formatShares(summary.buyShares)} shares across {summary.buys} orders
              </p>
            </CardContent>
          </Card>
          <Card size="sm">
            <CardHeader>
              <CardDescription className="text-xs tracking-wide uppercase">Sell</CardDescription>
              <CardTitle className="text-2xl tabular-nums text-destructive">
                {formatMoney(summary.sellNotional)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {formatShares(summary.sellShares)} shares across {summary.sells} orders
              </p>
            </CardContent>
          </Card>
          <Card size="sm">
            <CardHeader>
              <CardDescription className="text-xs tracking-wide uppercase">
                Net cash estimate
              </CardDescription>
              <CardTitle
                className={cn(
                  'text-2xl tabular-nums',
                  summary.netNotional > 0
                    ? 'text-[#3f6d7e]'
                    : summary.netNotional < 0
                      ? 'text-destructive'
                      : undefined,
                )}
              >
                {formatMoney(summary.netNotional)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {activeLabel}
                {tradeRun ? ` · ${tradeRun.result.strategy}` : ''}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!tradeRun ? (
        <Card>
          <CardHeader>
            <CardTitle>No run to trade from</CardTitle>
            <CardDescription>
              {activeId
                ? loading
                  ? `Loading runs for ${activeLabel}…`
                  : `Select a saved optimization run, or run analysis for ${activeLabel} first.`
                : 'Select a saved portfolio with an optimization run, or create a new analysis.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link to="/analyze">Go to Portfolio analysis</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="border-b border-border/70 bg-muted/30">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <CardDescription className="text-xs tracking-wide uppercase">
                  Order blotter
                </CardDescription>
                <CardTitle className="text-lg">Review before send</CardTitle>
                <CardDescription className="mt-1">
                  Whole-share market orders for {tradeRun.result.period_start} –{' '}
                  {tradeRun.result.period_end} · capital {formatMoney(tradeRun.capital)}. Edit or
                  remove lines, then submit to the selected account.
                </CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="outline" onClick={resetOrders}>
                  Reset to plan
                </Button>
                <Button
                  type="button"
                  disabled={submitting || orders.length === 0 || !canRouteLive}
                  onClick={() => void handleSubmit()}
                >
                  {submitting
                    ? 'Submitting…'
                    : canRouteLive
                      ? `Submit to ${brokerageLabel(brokerage)}`
                      : 'Select destination to submit'}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {orders.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No whole-share buys or sells needed for this run.
              </p>
            ) : (
              <div className="overflow-hidden rounded-lg border border-border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/40 hover:bg-muted/40">
                      <TableHead>Symbol</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead className="text-right">Shares</TableHead>
                      <TableHead className="text-right">Est. notional</TableHead>
                      <TableHead className="text-right">Weight</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orders.map((order) => {
                      const notional =
                        order.price != null && order.price > 0
                          ? order.quantity * order.price
                          : null
                      return (
                        <TableRow key={order.id}>
                          <TableCell>
                            <div className="font-medium tracking-wide">{order.symbol}</div>
                            <div className="text-xs text-muted-foreground">{order.name}</div>
                          </TableCell>
                          <TableCell>{sideBadge(order.side)}</TableCell>
                          <TableCell className="text-right">
                            <Input
                              className="ml-auto h-8 w-24 text-right tabular-nums"
                              inputMode="numeric"
                              pattern="[0-9]*"
                              value={qtyDrafts[order.id] ?? ''}
                              aria-label={`${order.symbol} whole shares`}
                              onChange={(event) => {
                                const raw = event.target.value
                                if (raw !== '' && !/^\d+$/.test(raw)) return
                                setQtyDrafts((current) => ({
                                  ...current,
                                  [order.id]: raw,
                                }))
                              }}
                              onBlur={() => commitQuantity(order.id)}
                              onKeyDown={(event) => {
                                if (event.key === 'Enter') {
                                  event.currentTarget.blur()
                                }
                              }}
                            />
                          </TableCell>
                          <TableCell className="text-right tabular-nums font-medium">
                            {formatMoney(notional)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-muted-foreground">
                            {formatWeight(order.currentWeight)} →{' '}
                            {formatWeight(order.targetWeight)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="text-destructive"
                              onClick={() => {
                                setOrders((current) =>
                                  current.filter((row) => row.id !== order.id),
                                )
                                setQtyDrafts((current) => {
                                  const next = { ...current }
                                  delete next[order.id]
                                  return next
                                })
                              }}
                            >
                              Remove
                            </Button>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            )}

            {submitNote && (
              <Alert
                variant={
                  submitResults?.some((row) => row.status === 'rejected')
                    ? 'destructive'
                    : undefined
                }
              >
                <AlertDescription>{submitNote}</AlertDescription>
              </Alert>
            )}

            {submitResults && submitResults.length > 0 && (
              <div className="overflow-hidden rounded-lg border border-border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/40 hover:bg-muted/40">
                      <TableHead>Symbol</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead className="text-right">Shares</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Detail</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {submitResults.map((row, index) => (
                      <TableRow key={`${row.symbol}-${row.side}-${index}`}>
                        <TableCell className="font-medium tracking-wide">{row.symbol}</TableCell>
                        <TableCell>{sideBadge(row.side)}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatShares(row.quantity)}
                        </TableCell>
                        <TableCell>
                          {row.status === 'accepted' ? (
                            <Badge variant="secondary">Accepted</Badge>
                          ) : (
                            <Badge variant="destructive">Rejected</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {row.order_id ? `Order ${row.order_id}` : row.message ?? '—'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
          <CardFooter className="justify-between gap-3 text-xs text-muted-foreground">
            <span>
              Destination:{' '}
              {canRouteLive && selectedAccount
                ? `${brokerageLabel(brokerage)} ${maskAccountNumber(selectedAccount.account_number)}`
                : 'not ready'}
            </span>
            <span>Market · day · whole shares</span>
          </CardFooter>
        </Card>
      )}
    </div>
  )
}
