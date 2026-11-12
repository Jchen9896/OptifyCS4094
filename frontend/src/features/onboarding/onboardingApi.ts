import { ApiError, fetchJson } from '../../lib/apiClient.ts'

export type QuestionOption = { id: string; label: string }

export type Question = { id: string; prompt: string; options: QuestionOption[] }

export type Questionnaire = { version: number; questions: Question[] }

export type RiskRecommendation = {
  strategy: 'min_variance' | 'max_sharpe' | 'target_risk'
  max_weight: number
  target_volatility: number | null
  checked: boolean
  notes: string[]
}

export type RiskProfile = {
  portfolio_id: string
  questionnaire_version: number
  answers: Record<string, string>
  capacity_score: number
  willingness_score: number
  score: number
  level: string
  label: string
  recommendation: RiskRecommendation
  updated_at: string
}

/** Analysis form values, in the percent text format that the analysis page uses. */
export type AnalysisSettings = {
  strategy: string
  maxWeightPercent: string
  targetVolatilityPercent: string
}

/** Router state that the Apply button sends to the analysis page. */
export type RecommendedSettingsState = { recommendedSettings: AnalysisSettings }

// The analysis form shows percents with at most this many decimals.
const PERCENT_DECIMALS = 1

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` }
}

function riskProfilePath(portfolioId: string): string {
  return `/api/portfolios/${encodeURIComponent(portfolioId)}/risk-profile`
}

export function getQuestionnaire(token: string): Promise<Questionnaire> {
  return fetchJson('/api/onboarding/questionnaire', { headers: authHeaders(token) })
}

export function saveRiskProfile(
  token: string,
  portfolioId: string,
  answers: Record<string, string>,
): Promise<RiskProfile> {
  return fetchJson(riskProfilePath(portfolioId), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
    body: JSON.stringify({ answers }),
  })
}

/** Return null when the portfolio has no profile yet. Other errors are thrown. */
export async function readRiskProfile(token: string, portfolioId: string): Promise<RiskProfile | null> {
  try {
    return await fetchJson<RiskProfile>(riskProfilePath(portfolioId), { headers: authHeaders(token) })
  } catch (caught) {
    if (caught instanceof ApiError && caught.code === 'risk_profile_not_found') return null
    throw caught
  }
}

/** Keep only the earlier answers that are still options in this questionnaire. */
export function keepValidAnswers(
  questionnaire: Questionnaire,
  answers: Record<string, string>,
): Record<string, string> {
  const kept: Record<string, string> = {}
  for (const question of questionnaire.questions) {
    const answer = answers[question.id]
    if (question.options.some((option) => option.id === answer)) kept[question.id] = answer
  }
  return kept
}

function percentText(value: number): string {
  return String(Number((value * 100).toFixed(PERCENT_DECIMALS)))
}

export function recommendationToAnalysisSettings(recommendation: RiskRecommendation): AnalysisSettings {
  return {
    strategy: recommendation.strategy,
    maxWeightPercent: percentText(recommendation.max_weight),
    targetVolatilityPercent:
      recommendation.target_volatility == null ? '' : percentText(recommendation.target_volatility),
  }
}
