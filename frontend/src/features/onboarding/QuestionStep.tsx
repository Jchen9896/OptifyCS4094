import { cn } from 'cn'
import type { Question } from './onboardingApi.ts'

type QuestionStepProps = {
  question: Question
  index: number
  total: number
  selectedOptionId: string | undefined
  onSelect: (optionId: string) => void
}

export default function QuestionStep({ question, index, total, selectedOptionId, onSelect }: QuestionStepProps) {
  const progressPercent = ((index + 1) / total) * 100
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">
          Question {index + 1} of {total}
        </p>
        <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-primary transition-all" style={{ width: `${progressPercent}%` }} />
        </div>
      </div>
      <h2 id={`question-${question.id}`} className="font-heading text-lg font-medium">
        {question.prompt}
      </h2>
      <div role="radiogroup" aria-labelledby={`question-${question.id}`} className="grid gap-2">
        {question.options.map((option) => {
          const selected = option.id === selectedOptionId
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onSelect(option.id)}
              className={cn(
                'rounded-lg border px-4 py-3 text-left text-sm transition-colors',
                selected ? 'border-primary bg-primary/10 text-foreground' : 'border-border hover:bg-muted',
              )}
            >
              {option.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
