import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatPercent } from '@/lib/formatters'
import { formatOptimizationRunStrategy } from '../optimization/optimizationApi.ts'
import type { RiskProfile } from './onboardingApi.ts'

type RiskProfileResultProps = {
  profile: RiskProfile
  applying: boolean
  onApply: () => void
  onRetake: () => void
}

export default function RiskProfileResult({ profile, applying, onApply, onRetake }: RiskProfileResultProps) {
  const recommendation = profile.recommendation
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <p className="text-xs text-muted-foreground">Your risk profile for this portfolio</p>
        <h2 className="font-heading text-2xl font-semibold">{profile.label}</h2>
        <p className="text-sm text-muted-foreground">
          Score {Math.round(profile.score)} / 100 · Capacity {Math.round(profile.capacity_score)} ·
          Willingness {Math.round(profile.willingness_score)}
        </p>
        <p className="text-xs text-muted-foreground">
          Your score is the lower of how much risk you can afford (capacity) and how much you accept
          (willingness).
        </p>
      </div>

      <div className="space-y-3 rounded-lg border border-border p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-medium">Recommended settings</h3>
          <Badge variant={recommendation.checked ? 'secondary' : 'outline'}>
            {recommendation.checked ? 'Checked on your holdings' : 'Not checked'}
          </Badge>
        </div>
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Strategy</dt>
          <dd>{formatOptimizationRunStrategy(recommendation.strategy)}</dd>
          <dt className="text-muted-foreground">Maximum weight per asset</dt>
          <dd>{formatPercent(recommendation.max_weight)}</dd>
          {recommendation.target_volatility != null && (
            <>
              <dt className="text-muted-foreground">Target annual volatility</dt>
              <dd>{formatPercent(recommendation.target_volatility)}</dd>
            </>
          )}
        </dl>
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {recommendation.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </div>

      <p className="text-xs text-muted-foreground">
        This recommendation is educational. It is not investment advice. You can change the settings
        before you run an analysis.
      </p>

      <div className="flex flex-wrap gap-2">
        <Button onClick={onApply} disabled={applying}>
          {applying ? 'Opening analysis…' : 'Apply to analysis'}
        </Button>
        <Button variant="outline" onClick={onRetake} disabled={applying}>
          Retake questionnaire
        </Button>
      </div>
    </div>
  )
}
