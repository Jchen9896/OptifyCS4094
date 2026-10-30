import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ApiError } from '../../src/lib/apiClient.ts'
import {
  buildPortfolioRequest, createPortfolio, listPortfolios, readPortfolio, restorePortfolio,
  type PortfolioDraft, type SavedPortfolio,
} from '../../src/features/portfolio/portfolioApi.ts'

const USER = '22222222-2222-2222-2222-222222222222'
const ID = '11111111-1111-1111-1111-111111111111'

function draft(): PortfolioDraft {
  return {
    portfolioName: ' Core ', initialCapital: 1000, startDate: '2026-01-01', endDate: '2026-02-01',
    strategy: 'minvar', maxWeightPercent: 60, riskFreePercent: 4,
    referencePrices: { AAPL: 100, MSFT: 200 },
    holdings: [
      { symbol: 'AAPL', name: 'Apple Inc.', quoteType: null, weightPercent: 50, quantity: 5 },
      { symbol: 'MSFT', name: 'Microsoft', quoteType: null, weightPercent: 50, quantity: 2.5 },
    ],
  }
}

function saved(): SavedPortfolio {
  const body = buildPortfolioRequest(draft())
  return { id: ID, user_id: USER, name: body.name, created_at: '2026-10-29T12:00:00Z',
    setup: body.setup, holdings: body.holdings.map((h, i) => ({ ...h, name: draft().holdings[i].name })) }
}

test('save and restore retain inputs, weights, quantities, and reference prices', () => {
  const result = restorePortfolio(saved())
  assert.deepEqual(result, { ...draft(), portfolioName: 'Core' })
  assert.equal(buildPortfolioRequest(draft()).setup.max_weight, 0.6)
  assert.equal(buildPortfolioRequest(draft()).setup.risk_free_rate, 0.04)
})

test('round quantities to storage precision and reject values that round to zero', () => {
  const input = draft()
  input.holdings[0].quantity = 1.123456789
  assert.equal(buildPortfolioRequest(input).holdings[0].quantity, '1.123457')
  input.holdings[0].quantity = 0.0000001
  assert.throws(() => buildPortfolioRequest(input), /load prices/)
})

test('empty portfolios can be saved and restored', () => {
  const input = { ...draft(), holdings: [], referencePrices: {} }
  assert.deepEqual(buildPortfolioRequest(input).holdings, [])
  assert.deepEqual(restorePortfolio({ ...saved(), holdings: [], setup: buildPortfolioRequest(input).setup }).holdings, [])
})

test('invalid and incomplete inputs are rejected', () => {
  for (const changes of [
    { portfolioName: ' ' }, { initialCapital: 0 }, { initialCapital: Infinity },
    { startDate: '' }, { endDate: '2025-01-01' }, { maxWeightPercent: 101 },
    { riskFreePercent: NaN }, { referencePrices: {} },
    { holdings: [{ ...draft().holdings[0], weightPercent: 10 }] },
    { holdings: [{ ...draft().holdings[0], weightPercent: 100, quantity: 1e12 }] },
  ]) assert.throws(() => buildPortfolioRequest({ ...draft(), ...changes }))
})

test('legacy portfolios report missing setup inputs', () => {
  assert.throws(() => restorePortfolio({ ...saved(), setup: null }), /no saved setup/)
})

test('client sends owner-scoped create/list/detail requests and preserves API errors', async (t) => {
  const calls: { path: string; init?: RequestInit }[] = []
  t.mock.method(globalThis, 'fetch', async (path: string, init?: RequestInit) => {
    calls.push({ path, init })
    return new Response(JSON.stringify(saved()), { status: 200 })
  })
  await createPortfolio(` ${USER} `, draft())
  await listPortfolios(USER)
  await readPortfolio(USER, ID)
  assert.equal(calls[0].path, `/api/portfolios?user_id=${USER}`)
  assert.equal(calls[0].init?.method, 'POST')
  assert.deepEqual(JSON.parse(calls[0].init!.body as string), buildPortfolioRequest(draft()))
  assert.equal(calls[1].path, `/api/portfolios?user_id=${USER}`)
  assert.equal(calls[2].path, `/api/portfolios/${ID}?user_id=${USER}`)
  assert.throws(() => listPortfolios('bad'), /UUID/)
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({
    detail: { code: 'duplicate_portfolio_name', message: 'Name already exists.' },
  }), { status: 409 }))
  await assert.rejects(createPortfolio(USER, draft()), (error: unknown) =>
    error instanceof ApiError && error.code === 'duplicate_portfolio_name' && error.status === 409)
})
