import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '@clerk/react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ApiError } from '@/lib/apiClient'
import { useActivePortfolio } from '../portfolio/ActivePortfolioContext.tsx'
import QuestionStep from './QuestionStep.tsx'
import RiskProfileResult from './RiskProfileResult.tsx'
import {
  getQuestionnaire,
  keepValidAnswers,
  readRiskProfile,
  recommendationToAnalysisSettings,
  saveRiskProfile,
  type Questionnaire,
  type RecommendedSettingsState,
  type RiskProfile,
} from './onboardingApi.ts'

function errorText(caught: unknown, fallback: string): string {
  if (caught instanceof ApiError) return caught.message
  return caught instanceof Error ? caught.message : fallback
}

export default function RiskProfilePage() {
  const { portfolioId = '' } = useParams()
  const navigate = useNavigate()
  const { getToken } = useAuth()
  const { portfolios, activeId, selectPortfolio } = useActivePortfolio()
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null)
  const [profile, setProfile] = useState<RiskProfile | null>(null)
  const [retaking, setRetaking] = useState(false)
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const portfolioName = portfolios.find((row) => row.id === portfolioId)?.name ?? 'this portfolio'

  const token = useCallback(async () => {
    const value = await getToken()
    if (!value) throw new Error('Sign in to answer the questionnaire.')
    return value
  }, [getToken])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setBusy(true)
      setError(null)
      try {
        const authToken = await token()
        const [loadedQuestionnaire, loadedProfile] = await Promise.all([
          getQuestionnaire(authToken),
          readRiskProfile(authToken, portfolioId),
        ])
        if (cancelled) return
        setQuestionnaire(loadedQuestionnaire)
        setProfile(loadedProfile)
      } catch (caught) {
        if (!cancelled) setError(errorText(caught, 'Could not load the questionnaire.'))
      } finally {
        if (!cancelled) setBusy(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [portfolioId, token])

  function startRetake() {
    if (!questionnaire) return
    setAnswers(profile ? keepValidAnswers(questionnaire, profile.answers) : {})
    setStep(0)
    setRetaking(true)
  }

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      setProfile(await saveRiskProfile(await token(), portfolioId, answers))
      setRetaking(false)
    } catch (caught) {
      setError(errorText(caught, 'Could not save your answers.'))
    } finally {
      setBusy(false)
    }
  }

  async function applyToAnalysis() {
    if (!profile) return
    setBusy(true)
    try {
      if (activeId !== portfolioId) await selectPortfolio(portfolioId)
      const state: RecommendedSettingsState = {
        recommendedSettings: recommendationToAnalysisSettings(profile.recommendation),
      }
      navigate('/analyze', { state })
    } finally {
      setBusy(false)
    }
  }

  const questions = questionnaire?.questions ?? []
  const question = questions[step]
  const showQuestions = questionnaire != null && (profile == null || retaking)
  const isLastStep = step === questions.length - 1

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold">Risk profile</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Answer a few questions about your goals for {portfolioName}. Optify uses your answers to
          recommend analysis settings for this portfolio only.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent className="py-2">
          {busy && !questionnaire && <p className="text-sm text-muted-foreground">Loading…</p>}

          {showQuestions && question && (
            <div className="space-y-6">
              <QuestionStep
                question={question}
                index={step}
                total={questions.length}
                selectedOptionId={answers[question.id]}
                onSelect={(optionId) => setAnswers((current) => ({ ...current, [question.id]: optionId }))}
              />
              <div className="flex justify-between gap-2">
                <Button
                  variant="outline"
                  disabled={busy || step === 0}
                  onClick={() => setStep((current) => current - 1)}
                >
                  Back
                </Button>
                <Button
                  disabled={busy || !answers[question.id]}
                  onClick={() => (isLastStep ? void submit() : setStep((current) => current + 1))}
                >
                  {isLastStep ? (busy ? 'Saving…' : 'See my profile') : 'Next'}
                </Button>
              </div>
            </div>
          )}

          {!showQuestions && profile && (
            <RiskProfileResult
              profile={profile}
              applying={busy}
              onApply={() => void applyToAnalysis()}
              onRetake={startRetake}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
