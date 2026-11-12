import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ApiError } from '../../src/lib/apiClient.ts'
import {
  getQuestionnaire, readRiskProfile, recommendationToAnalysisSettings, saveRiskProfile,
  type RiskProfile, type RiskRecommendation,
} from '../../src/features/onboarding/onboardingApi.ts'

const ID = '11111111-1111-1111-1111-111111111111'
const TOKEN = 'token-1'

function recommendation(changes: Partial<RiskRecommendation> = {}): RiskRecommendation {
  return {
    strategy: 'target_risk', max_weight: 0.35, target_volatility: 0.12, checked: true, notes: [], ...changes,
  }
}

function profile(): RiskProfile {
  return {
    portfolio_id: ID, questionnaire_version: 1, answers: { goal: 'growth' }, capacity_score: 75,
    willingness_score: 50, score: 50, level: 'moderate', label: 'Moderate',
    recommendation: recommendation(), updated_at: '2026-11-11T12:00:00Z',
  }
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status })
}

test('maps a recommendation to analysis form percents', () => {
  assert.deepEqual(recommendationToAnalysisSettings(recommendation()), {
    strategy: 'target_risk', maxWeightPercent: '35', targetVolatilityPercent: '12',
  })
})

test('rounds caps such as 0.334 and leaves the target empty for other strategies', () => {
  assert.deepEqual(
    recommendationToAnalysisSettings(recommendation({ strategy: 'min_variance', max_weight: 0.334, target_volatility: null })),
    { strategy: 'min_variance', maxWeightPercent: '33.4', targetVolatilityPercent: '' },
  )
})

test('client sends authorized questionnaire, save, and read requests', async (t) => {
  const calls: { path: string; init?: RequestInit }[] = []
  t.mock.method(globalThis, 'fetch', async (path: string, init?: RequestInit) => {
    calls.push({ path, init })
    return jsonResponse(path.endsWith('questionnaire') ? { version: 1, questions: [] } : profile())
  })

  assert.equal((await getQuestionnaire(TOKEN)).version, 1)
  assert.equal((await saveRiskProfile(TOKEN, ID, { goal: 'growth' })).level, 'moderate')
  assert.equal((await readRiskProfile(TOKEN, ID))?.label, 'Moderate')

  assert.equal(calls[0].path, '/api/onboarding/questionnaire')
  assert.equal(calls[1].path, `/api/portfolios/${ID}/risk-profile`)
  assert.equal(calls[1].init?.method, 'PUT')
  assert.deepEqual(JSON.parse(calls[1].init!.body as string), { answers: { goal: 'growth' } })
  for (const call of calls) {
    assert.equal((call.init?.headers as Record<string, string>).Authorization, `Bearer ${TOKEN}`)
  }
})

test('read returns null for a missing profile and throws other errors', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => jsonResponse(
    { detail: { code: 'risk_profile_not_found', message: 'No profile.' } }, 404,
  ))
  assert.equal(await readRiskProfile(TOKEN, ID), null)

  t.mock.method(globalThis, 'fetch', async () => jsonResponse(
    { detail: { code: 'portfolio_not_found', message: 'The portfolio was not found.' } }, 404,
  ))
  await assert.rejects(readRiskProfile(TOKEN, ID), (error: unknown) =>
    error instanceof ApiError && error.code === 'portfolio_not_found')
})
